import boto3
import os
import json
import datetime
import time
import botocore
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
ddb = boto3.client('dynamodb')
s3 = boto3.client('s3')
ses = boto3.client('ses', region_name='ap-south-1')

DDB_TABLE_NAME = os.environ['DDB_TABLE_NAME']
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
SES_SENDER = os.environ['SES_SENDER']

def is_email_subscribed(email):
    try:
        response = ddb.get_item(
            TableName=DDB_TABLE_NAME,
            Key={'Email': {'S': email}}
        )
        return 'Item' in response
    except Exception as e:
        logger.error(f"DynamoDB check error for {email}: {e}")
        return False

def lambda_handler(event, context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    logger.info("Starting patch scan automation...")

    # Fetch EC2 instances with relevant tags
    reservations = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:PatchScanAutomation', 'Values': ['Enabled']},
            {'Name': 'tag:PatchScanAutomationWindow', 'Values': ['Daily']},
            {'Name': 'instance-state-name', 'Values': ['running']}  # Only running instances
        ]
    )['Reservations']

    instance_ids = []
    instance_map = {}

    for r in reservations:
        for inst in r['Instances']:
            iid = inst['InstanceId']
            tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])}
            email = tags.get('PatchScanEmailAlert')
            if email and "@" in email:
                private_ip = inst.get('PrivateIpAddress', 'N/A')
                hostname = inst.get('PrivateDnsName', 'N/A')
                instance_ids.append(iid)
                instance_map[iid] = {
                    'email': email,
                    'tags': tags,
                    'private_ip': private_ip,
                    'hostname': hostname
                }
                logger.info(f"Instance {iid} added for patch scan. Email: {email}, Private IP: {private_ip}")

    if not instance_ids:
        logger.info("No matching running instances found.")
        return

    try:
        logger.info(f"Sending patch scan command to instances: {instance_ids}")
        ssm.send_command(
            InstanceIds=instance_ids,
            DocumentName="AWS-RunPatchBaseline",
            Parameters={"Operation": ["Scan"]}
        )
    except Exception as e:
        logger.error(f"SendCommand failed: {e}")
        return

    time.sleep(20)  # Wait for scan to complete

    results = {}
    for iid in instance_ids:
        try:
            state = ssm.describe_instance_patch_states(InstanceIds=[iid])['InstancePatchStates'][0]
            results[iid] = {
                'ComplianceStatus': state.get('PatchComplianceStatus', 'Unknown'),
                'MissingCount': state.get('MissingCount', 0),
                'InstalledPendingRebootCount': state.get('InstalledPendingRebootCount', 0),
                'OperationStartTime': state.get('OperationStartTime').isoformat(),
                'OperationEndTime': state.get('OperationEndTime').isoformat()
            }
            logger.info(f"Patch scan result for {iid}: {results[iid]}")
        except Exception as e:
            logger.error(f"Patch state error for {iid}: {e}")
            continue

    # Save results to S3
    s3_key = f"scans/{today}-scan-results.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(results, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Saved scan results to S3 at {s3_key}")
    except Exception as e:
        logger.error(f"S3 upload error: {e}")

    # Send email per instance
    for iid, data in results.items():
        email = instance_map[iid]['email']
        private_ip = instance_map[iid]['private_ip']
        hostname = instance_map[iid]['hostname']
        missing = data.get('MissingCount', 0)
        pending = data.get('InstalledPendingRebootCount', 0)
        compliance = data.get('ComplianceStatus', 'Unknown')
        start_time = data.get('OperationStartTime')
        end_time = data.get('OperationEndTime')

        subject = (
            f"Patch Scan Report for {iid} | Private IP: {private_ip} | "
            f"Missing Patches: {missing} | Pending Reboot: {pending}"
        )

        body = (
            f"Patch Scan Report for {iid}\n\n"
            f"Hostname: {hostname}\n"
            f"Private IP: {private_ip}\n"
            f"Missing Patches: {missing}\n"
            f"Pending Reboot Patches: {pending}\n"
            f"Compliance Status: {compliance}\n"
            f"Operation Time: {start_time} to {end_time} UTC"
        )

        # Add email to DDB if not subscribed
        if not is_email_subscribed(email):
            try:
                ddb.put_item(TableName=DDB_TABLE_NAME, Item={'Email': {'S': email}})
                logger.info(f"Added new subscriber email {email} to DynamoDB.")
            except Exception as e:
                logger.error(f"Error saving {email} to DynamoDB: {e}")

        try:
            ses.send_email(
                Source=SES_SENDER,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body}}
                }
            )
            logger.info(f"Sent patch result for {iid} to {email}")
        except botocore.exceptions.ClientError as e:
            logger.error(f"SES error for {iid}: {e.response['Error']['Message']}")
