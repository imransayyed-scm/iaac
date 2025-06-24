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
# --- MODIFICATION: Add clients for STS and IAM ---
sts = boto3.client('sts')
iam = boto3.client('iam')


# Load Environment Variables
DDB_TABLE_NAME = os.environ['DDB_TABLE_NAME']
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
SES_SENDER = os.environ['SES_SENDER']


def is_email_subscribed(email):
    """Checks if an email address already exists in the DynamoDB table."""
    try:
        response = ddb.get_item(
            TableName=DDB_TABLE_NAME,
            Key={'Email': {'S': email}}
        )
        return 'Item' in response
    except botocore.exceptions.ClientError as e:
        logger.error(f"DynamoDB check error for {email}: {e.response['Error']['Message']}")
        return False

# --- MODIFICATION: Helper function to get Account ID and Alias ---
def get_account_details():
    """Gets the AWS Account ID and Alias."""
    try:
        # Get Account ID from the caller identity
        account_id = sts.get_caller_identity()['Account']
        
        # Get Account Alias
        response = iam.list_account_aliases()
        aliases = response.get('AccountAliases', [])
        
        # Use the first alias if available, otherwise fall back to the account ID
        account_name = aliases[0] if aliases else account_id
        
        return account_id, account_name
        
    except botocore.exceptions.ClientError as e:
        logger.error(f"Could not get account details: {e}. Defaulting to Account ID only.")
        # Fallback in case of permission errors
        try:
            account_id = sts.get_caller_identity()['Account']
            return account_id, account_id
        except Exception as inner_e:
            logger.error(f"Could not even get Account ID: {inner_e}")
            return "Unknown", "Unknown"


def lambda_handler(event, context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # --- MODIFICATION: Get account details at the start ---
    account_id, account_name = get_account_details()
    logger.info(f"Running in AWS Account: {account_name} ({account_id})")

    logger.info("Starting patch scan automation...")

    # Fetch EC2 instances with relevant tags that are currently running
    reservations = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:PatchScanAutomation', 'Values': ['Enabled']},
            {'Name': 'tag:PatchScanAutomationWindow', 'Values': ['Daily']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )['Reservations']

    instance_ids = []
    instance_map = {}
    unique_email_recipients = set()

    for r in reservations:
        for inst in r['Instances']:
            instance_id = inst['InstanceId']
            tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])}
            email = tags.get('PatchScanEmailAlert')

            if email and "@" in email:
                private_ip = inst.get('PrivateIpAddress', 'N/A')
                hostname = inst.get('PrivateDnsName', 'N/A')
                instance_ids.append(instance_id)
                instance_map[instance_id] = {
                    'email': email, 'tags': tags, 'private_ip': private_ip, 'hostname': hostname
                }
                unique_email_recipients.add(email)
                logger.info(f"Instance {instance_id} added for patch scan. Email: {email}")

    if not instance_ids:
        logger.info("No matching running instances found to scan.")
        return {'statusCode': 200, 'body': 'No instances to scan.'}

    # Send SSM command
    try:
        response = ssm.send_command(
            InstanceIds=instance_ids, DocumentName="AWS-RunPatchBaseline", Parameters={"Operation": ["Scan"]}
        )
        command_id = response['Command']['CommandId']
        logger.info(f"SSM Command sent. CommandId: {command_id}")
    except botocore.exceptions.ClientError as e:
        logger.error(f"SendCommand failed: {e.response['Error']['Message']}")
        return {'statusCode': 500, 'body': 'Failed to send SSM command.'}

    # Wait for command completion
    waiter = ssm.get_waiter('command_executed')
    for instance_id in instance_ids:
        logger.info(f"Waiting for command {command_id} to complete on instance {instance_id}...")
        try:
            waiter.wait(
                CommandId=command_id, InstanceId=instance_id, WaiterConfig={'Delay': 30, 'MaxAttempts': 10}
            )
        except botocore.exceptions.WaiterError as e:
            logger.error(f"Waiter failed for instance {instance_id}: {e}")
            continue

    # Fetch results
    results = {}
    non_compliant_count = 0
    for iid in instance_ids:
        try:
            state = ssm.describe_instance_patch_states(InstanceIds=[iid])['InstancePatchStates'][0]
            compliance_status = state.get('PatchComplianceStatus', 'Unknown')
            if compliance_status != 'COMPLIANT':
                non_compliant_count += 1
            results[iid] = {
                'ComplianceStatus': compliance_status,
                'MissingCount': state.get('MissingCount', 0),
                'InstalledPendingRebootCount': state.get('InstalledPendingRebootCount', 0)
            }
        except (botocore.exceptions.ClientError, IndexError) as e:
            logger.error(f"Could not retrieve patch state for instance {iid}: {e}")
            results[iid] = {'ComplianceStatus': 'ERROR', 'MissingCount': 'N/A', 'InstalledPendingRebootCount': 'N/A'}
            non_compliant_count += 1

    # Save results to S3
    s3_key = f"scans/{today}-scan-results.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME, Key=s3_key, Body=json.dumps(results, indent=2), ContentType="application/json"
        )
        logger.info(f"Saved aggregated scan results to S3 at s3://{S3_BUCKET_NAME}/{s3_key}")
    except botocore.exceptions.ClientError as e:
        logger.error(f"S3 upload error: {e.response['Error']['Message']}")

    if not unique_email_recipients:
        logger.warning("No email recipients found. Skipping email notification.")
        return {'statusCode': 200, 'body': 'Process completed, no emails to send.'}
        
    # Build HTML table for the email
    html_table_rows = ""
    for iid in instance_ids:
        res = results.get(iid, {})
        inst_details = instance_map.get(iid, {})
        status = res.get('ComplianceStatus', 'Unknown')
        status_color = "red" if status != 'COMPLIANT' else "green"
        html_table_rows += f"""
        <tr>
            <td>{iid}</td>
            <td>{inst_details.get('hostname', 'N/A')}</td>
            <td>{inst_details.get('private_ip', 'N/A')}</td>
            <td style="color:{status_color}; font-weight:bold;">{status}</td>
            <td>{res.get('MissingCount', 'N/A')}</td>
            <td>{res.get('InstalledPendingRebootCount', 'N/A')}</td>
        </tr>
        """

    # --- MODIFICATION: Add account name to email subject and body ---
    subject = f"[{account_name}] Daily Patch Scan Summary: {non_compliant_count} Non-Compliant Instances"
    
    html_body = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
    </head>
    <body>
      <h2>Aggregated Patch Scan Report - {today}</h2>
      <p><strong>AWS Account:</strong> {account_name} ({account_id})</p>
      <hr>
      <p>This report summarizes the patch compliance status for all monitored instances.</p>
      <table>
        <thead>
          <tr>
            <th>Instance ID</th>
            <th>Hostname</th>
            <th>Private IP</th>
            <th>Compliance Status</th>
            <th>Missing Patches</th>
            <th>Pending Reboot</th>
          </tr>
        </thead>
        <tbody>
          {html_table_rows}
        </tbody>
      </table>
      <br>
      <p><i>A detailed JSON report is available in S3: s3://{S3_BUCKET_NAME}/{s3_key}</i></p>
    </body>
    </html>
    """

    # Add new emails to DynamoDB and send the aggregated email
    for email in unique_email_recipients:
        if not is_email_subscribed(email):
            try:
                ddb.put_item(TableName=DDB_TABLE_NAME, Item={'Email': {'S': email}})
            except botocore.exceptions.ClientError as e:
                logger.error(f"Error saving {email} to DynamoDB: {e.response['Error']['Message']}")

    try:
        recipient_list = list(unique_email_recipients)
        ses.send_email(
            Source=SES_SENDER,
            Destination={'ToAddresses': recipient_list},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
        )
        logger.info(f"Successfully sent aggregated report to: {', '.join(recipient_list)}")
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to send aggregated email: {e.response['Error']['Message']}")

    logger.info("Patch scan automation finished.")
    return {'statusCode': 200, 'body': json.dumps('Aggregated report sent successfully.')}
