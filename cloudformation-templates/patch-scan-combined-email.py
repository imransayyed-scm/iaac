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

# Load environment variables
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
    except Exception as e:
        logger.error(f"Could not get account details: {e}")
        return "Unknown", "Unknown"

def lambda_handler(event, context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    account_id, account_name = get_account_details()
    logger.info(f"Running in AWS Account: {account_name} ({account_id})")

    reservations = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:PatchScanAutomation', 'Values': ['Enabled']},
            {'Name': 'tag:PatchScanAutomationWindow', 'Values': ['Daily']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )['Reservations']

    instance_ids = []
    instance_map = {}
    email_recipients = set()

    for r in reservations:
        for inst in r['Instances']:
            instance_id = inst['InstanceId']
            tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])}
            email = tags.get('PatchScanEmailAlert')
            if email and "@" in email:
                instance_ids.append(instance_id)
                instance_map[instance_id] = {
                    'email': email,
                    'tags': tags,
                    'private_ip': inst.get('PrivateIpAddress', 'N/A'),
                    'hostname': inst.get('PrivateDnsName', 'N/A'),
                    'name': tags.get('Name', 'N/A')
                }
                email_recipients.add(email)

    if not instance_ids:
        logger.info("No matching running instances found.")
        return {'statusCode': 200, 'body': 'No instances found for scan.'}

    try:
        command_id = ssm.send_command(
            InstanceIds=instance_ids,
            DocumentName="AWS-RunPatchBaseline",
            Parameters={"Operation": ["Scan"]}
        )['Command']['CommandId']
        logger.info(f"Patch scan command sent: {command_id}")
    except Exception as e:
        logger.error(f"SSM SendCommand failed: {e}")
        return {'statusCode': 500, 'body': 'Failed to send SSM command.'}

    waiter = ssm.get_waiter('command_executed')
    for iid in instance_ids:
        try:
            waiter.wait(CommandId=command_id, InstanceId=iid, WaiterConfig={'Delay': 30, 'MaxAttempts': 10})
        except Exception as e:
            logger.warning(f"Command not completed on {iid}: {e}")

    results = {}
    non_compliant_count = 0

    for iid in instance_ids:
        try:
            state = ssm.describe_instance_patch_states(InstanceIds=[iid])['InstancePatchStates'][0]
            missing = state.get('MissingCount', 0)
            pending = state.get('InstalledPendingRebootCount', 0)
            if missing > 0 or pending > 0:
                compliance_status = "🔴 Non Compliant"
                non_compliant_count += 1
            else:
                compliance_status = "🟢 Compliant"
            results[iid] = {
                'ComplianceStatus': compliance_status,
                'MissingCount': missing,
                'InstalledPendingRebootCount': pending
            }
        except Exception as e:
            logger.error(f"Error fetching patch state for {iid}: {e}")
            results[iid] = {
                'ComplianceStatus': "⚠️ Error",
                'MissingCount': 'N/A',
                'InstalledPendingRebootCount': 'N/A'
            }
            non_compliant_count += 1

    # Upload result to S3
    s3_key = f"scans/{today}-scan-results.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(results, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Uploaded result to s3://{S3_BUCKET_NAME}/{s3_key}")
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")

    # Compose HTML table
    html_table = ""
    for idx, iid in enumerate(instance_ids, start=1):
        meta = instance_map.get(iid, {})
        res = results.get(iid, {})
        html_table += f"""
        <tr>
            <td>{idx}</td>
            <td>{iid}</td>
            <td>{meta.get('name', 'N/A')}</td>
            <td>{meta.get('hostname', 'N/A')}</td>
            <td>{meta.get('private_ip', 'N/A')}</td>
            <td>{res.get('ComplianceStatus')}</td>
            <td>{res.get('MissingCount')}</td>
            <td>{res.get('InstalledPendingRebootCount')}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <head>
      <style>
        table {{ border-collapse: collapse; width: 100%; font-family: Arial; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
      </style>
    </head>
    <body>
      <h2>Aggregated Patch Scan Report - {today}</h2>
      <p><strong>AWS Account:</strong> {account_name} ({account_id})</p>
      <table>
        <thead>
          <tr>
            <th>Sr. No.</th>
            <th>Instance ID</th>
            <th>Name</th>
            <th>Hostname</th>
            <th>Private IP</th>
            <th>Compliance Status</th>
            <th>Missing Patches</th>
            <th>Pending Reboot</th>
          </tr>
        </thead>
        <tbody>
          {html_table}
        </tbody>
      </table>
      <p><i>Detailed results in S3: s3://{S3_BUCKET_NAME}/{s3_key}</i></p>
    </body>
    </html>
    """

    subject = f"[{account_name}] Patch Scan Report: {non_compliant_count} Non-Compliant Instances"

    for email in email_recipients:
        if not is_email_subscribed(email):
            try:
                ddb.put_item(TableName=DDB_TABLE_NAME, Item={'Email': {'S': email}})
            except Exception as e:
                logger.warning(f"Could not add {email} to DynamoDB: {e}")

    try:
        ses.send_email(
            Source=SES_SENDER,
            Destination={'ToAddresses': list(email_recipients)},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
        )
        logger.info("Email sent to recipients.")
    except Exception as e:
        logger.error(f"SES send_email failed: {e}")

    return {'statusCode': 200, 'body': 'Patch scan report sent.'}
