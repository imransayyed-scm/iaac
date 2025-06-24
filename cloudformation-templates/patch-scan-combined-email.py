import boto3
import os
import json
import datetime
import botocore
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize boto3 clients
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
ddb = boto3.client('dynamodb')
s3 = boto3.client('s3')
ses = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
sts = boto3.client('sts')
iam = boto3.client('iam')

# Load Environment Variables
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
    except botocore.exceptions.ClientError as e:
        logger.error(f"DynamoDB check error for {email}: {e.response['Error']['Message']}")
        return False


def get_account_details():
    try:
        account_id = sts.get_caller_identity()['Account']
        aliases = iam.list_account_aliases().get('AccountAliases', [])
        account_name = aliases[0] if aliases else account_id
        return account_id, account_name
    except botocore.exceptions.ClientError as e:
        logger.error(f"Could not get account details: {e}")
        return "Unknown", "Unknown"


def lambda_handler(event, context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    account_id, account_name = get_account_details()

    logger.info("Starting patch scan automation...")

    reservations = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:PatchScanAutomation', 'Values': ['Enabled']},
            {'Name': 'tag:PatchScanAutomationWindow', 'Values': ['Daily']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )['Reservations']

    instance_ids, instance_map, unique_email_recipients = [], {}, set()

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
                unique_email_recipients.add(email)

    if not instance_ids:
        logger.info("No instances found.")
        return {'statusCode': 200, 'body': 'No instances found.'}

    try:
        command = ssm.send_command(
            InstanceIds=instance_ids,
            DocumentName="AWS-RunPatchBaseline",
            Parameters={"Operation": ["Scan"]}
        )
        command_id = command['Command']['CommandId']
    except botocore.exceptions.ClientError as e:
        logger.error(f"SSM error: {e}")
        return {'statusCode': 500, 'body': 'SSM command failed.'}

    waiter = ssm.get_waiter('command_executed')
    for iid in instance_ids:
        try:
            waiter.wait(CommandId=command_id, InstanceId=iid, WaiterConfig={'Delay': 30, 'MaxAttempts': 10})
        except Exception as e:
            logger.warning(f"Waiter timeout for instance {iid}: {e}")

    results = {}
    non_compliant_count = 0

    for iid in instance_ids:
        try:
            state = ssm.describe_instance_patch_states(InstanceIds=[iid])['InstancePatchStates'][0]
            missing = state.get('MissingCount', 0)
            pending = state.get('InstalledPendingRebootCount', 0)
            if missing > 0 or pending > 0:
                compliance = "🔴 Non Compliant"
                non_compliant_count += 1
            else:
                compliance = "🟢 Compliant"

            results[iid] = {
                'ComplianceStatus': compliance,
                'MissingCount': missing,
                'InstalledPendingRebootCount': pending
            }
        except Exception as e:
            logger.error(f"Patch state error for {iid}: {e}")
            results[iid] = {
                'ComplianceStatus': 'ERROR',
                'MissingCount': 'N/A',
                'InstalledPendingRebootCount': 'N/A'
            }
            non_compliant_count += 1

    s3_key = f"scans/{today}-scan-results.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(results, indent=2),
            ContentType="application/json"
        )
    except Exception as e:
        logger.error(f"S3 upload error: {e}")

    html_table = ""
    for iid in instance_ids:
        res = results[iid]
        meta = instance_map.get(iid, {})
        status = res.get('ComplianceStatus', 'Unknown')
        html_table += f"""
        <tr>
            <td>{iid}</td>
            <td>{meta.get('hostname', 'N/A')}</td>
            <td>{meta.get('private_ip', 'N/A')}</td>
            <td>{status}</td>
            <td>{res.get('MissingCount', 'N/A')}</td>
            <td>{res.get('InstalledPendingRebootCount', 'N/A')}</td>
        </tr>"""

    subject = f"[{account_name}] Daily Patch Scan Summary: {non_compliant_count} Non-Compliant Instances"
    html_body = f"""
    <html><body>
    <h2>Aggregated Patch Scan Report - {today}</h2>
    <p><strong>AWS Account:</strong> {account_name} ({account_id})</p>
    <table border="1" style="border-collapse: collapse;">
    <tr>
      <th>Instance ID</th>
      <th>Hostname</th>
      <th>Private IP</th>
      <th>Compliance Status</th>
      <th>Missing Patches</th>
      <th>Pending Reboot</th>
    </tr>
    {html_table}
    </table>
    <p>Detailed report: s3://{S3_BUCKET_NAME}/{s3_key}</p>
    </body></html>"""

    for email in unique_email_recipients:
        if not is_email_subscribed(email)
            try:
                ddb.put_item(TableName=DDB_TABLE_NAME, Item={'Email': {'S': email}})
            except Exception as e:
                logger.error(f"DynamoDB put_item error: {e}")

    try:
        ses.send_email(
            Source=SES_SENDER,
            Destination={'ToAddresses': list(unique_email_recipients)},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
        )
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"SES send_email error: {e}")

    return {'statusCode': 200, 'body': 'Aggregated report sent.'}
