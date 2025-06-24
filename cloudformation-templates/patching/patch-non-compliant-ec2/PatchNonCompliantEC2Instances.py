import boto3
import json
import time

ssm_client = boto3.client('ssm')
ec2_client = boto3.client('ec2')
ses_client = boto3.client('ses')

SENDER_EMAIL = 'no-reply@piramal.info'
TAG_KEY = 'PatchDeployAutomation'
TAG_VALUE = 'Enabled'
EMAIL_TAG = 'PatchScanEmailAlert'
POLL_INTERVAL = 30
MAX_WAIT_TIME = 900  # seconds

def get_tagged_instances():
    instances = []
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            email = None
            for tag in instance.get('Tags', []):
                if tag['Key'] == EMAIL_TAG:
                    email = tag['Value']
            if email:
                instances.append({
                    'InstanceId': instance['InstanceId'],
                    'PrivateIp': instance.get('PrivateIpAddress'),
                    'Hostname': instance.get('PrivateDnsName'),
                    'Email': email
                })
    return instances

def get_patch_state(instance_id):
    state = ssm_client.describe_instance_patch_states(InstanceIds=[instance_id])['InstancePatchStates'][0]
    return {
        'MissingPatches': state.get('MissingCount', 0),
        'PendingReboot': state.get('InstalledPendingRebootCount', 0),
        'ComplianceStatus': state.get('PatchState', 'Unknown'),
        'OperationStart': state.get('OperationStartTime', ''),
        'OperationEnd': state.get('OperationEndTime', '')
    }

def send_email(instance, patch_data, stage):
    subject = f"Patch Scan Report for {instance['InstanceId']} | Private IP: {instance['PrivateIp']} | Missing Patches: {patch_data['MissingPatches']} | Pending Reboot: {patch_data['PendingReboot']}"
    body = f"""
Patch {stage} Report for {instance['InstanceId']}

Hostname: {instance['Hostname']}
Private IP: {instance['PrivateIp']}
Missing Patches: {patch_data['MissingPatches']}
Pending Reboot Patches: {patch_data['PendingReboot']}
Compliance Status: {patch_data['ComplianceStatus']}
Operation Time: {patch_data['OperationStart']} to {patch_data['OperationEnd']} UTC
"""
    ses_client.send_email(
        Source=SENDER_EMAIL,
        Destination={'ToAddresses': [instance['Email']]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )

def wait_for_command(command_id, instance_id):
    elapsed = 0
    while elapsed < MAX_WAIT_TIME:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        invocations = ssm_client.list_command_invocations(
            CommandId=command_id,
            InstanceId=instance_id,
            Details=True
        )['CommandInvocations']
        if invocations and invocations[0]['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            return invocations[0]['Status']
    return "TimedOut"

def lambda_handler(event, context):
    all_instances = get_tagged_instances()
    if not all_instances:
        return {'statusCode': 200, 'body': 'No tagged instances found.'}

    compliance = ssm_client.describe_instance_patch_states(
        InstanceIds=[i['InstanceId'] for i in all_instances]
    )

    non_compliant = []
    for state in compliance['InstancePatchStates']:
        if state.get('CriticalNonCompliantCount', 0) > 0 or state.get('SecurityNonCompliantCount', 0) > 0:
            for i in all_instances:
                if i['InstanceId'] == state['InstanceId']:
                    patch_data = get_patch_state(i['InstanceId'])
                    send_email(i, patch_data, "Pre-Patch")
                    non_compliant.append(i)

    if not non_compliant:
        return {'statusCode': 200, 'body': 'All tagged instances are compliant.'}

    ids_to_patch = [i['InstanceId'] for i in non_compliant]
    command = ssm_client.send_command(
        InstanceIds=ids_to_patch,
        DocumentName='AWS-RunPatchBaseline',
        Parameters={'Operation': ['Install']},
        TimeoutSeconds=900,
        Comment='Patch triggered by Lambda'
    )

    for instance in non_compliant:
        wait_for_command(command['Command']['CommandId'], instance['InstanceId'])
        updated_patch_data = get_patch_state(instance['InstanceId'])
        send_email(instance, updated_patch_data, "Post-Patch")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Patch workflow complete.',
            'patchedInstances': ids_to_patch,
            'commandId': command['Command']['CommandId']
        })
    }



CloudShell
Feedback
