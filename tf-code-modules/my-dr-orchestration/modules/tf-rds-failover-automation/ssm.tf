# tf-rds-failover-automation/ssm.tf

resource "aws_ssm_document" "rds_failover_document" {
  name            = var.ssm_document_name
  document_type   = "Automation"
  document_format = "YAML" # Terraform aws_ssm_document uses this for YAML content
  tags            = var.tags

  content = <<-YAML
description: RDS failover + SG update + target refresh
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
parameters:
  DBInstanceIdentifier:
    type: String
    description: RDS DB Instance Identifier
  AutomationAssumeRole:
    type: String
    description: IAM Role for Automation
  TargetSecurityGroupId:
    type: String
    description: (Required) The Security Group ID to update for RDS access.
  DrInstance1CidrIp:
    type: String
    description: (Required) CIDR IP for DR instance 1 (e.g., app server).
  DrInstance2CidrIp:
    type: String
    description: (Required) CIDR IP for DR instance 2 (e.g., app server).
  LambdaFunctionName:
    type: String
    description: (Required) Name of the Lambda function to invoke for target registration.

mainSteps:
  - name: RebootRDS
    action: aws:executeAwsApi
    inputs:
      Service: rds
      Api: RebootDBInstance
      DBInstanceIdentifier: '{{ DBInstanceIdentifier }}'
      ForceFailover: true

  - name: AddIngressForDR1
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: AuthorizeSecurityGroupIngress
      GroupId: '{{ TargetSecurityGroupId }}'
      IpPermissions:
        - IpProtocol: tcp
          FromPort: 3306
          ToPort: 3306
          IpRanges:
            - CidrIp: '{{ DrInstance1CidrIp }}'
              Description: "Allow DB access from DR Instance 1 (Automated)"

  - name: AddIngressForDR2
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: AuthorizeSecurityGroupIngress
      GroupId: '{{ TargetSecurityGroupId }}'
      IpPermissions:
        - IpProtocol: tcp
          FromPort: 3306
          ToPort: 3306
          IpRanges:
            - CidrIp: '{{ DrInstance2CidrIp }}'
              Description: "Allow DB access from DR Instance 2 (Automated)"

  - name: WaitForRDSAvailable
    action: aws:waitForAwsResourceProperty
    timeoutSeconds: 1800 # 30 minutes, adjust as needed
    inputs:
      Service: rds
      Api: DescribeDBInstances
      DBInstanceIdentifier: '{{ DBInstanceIdentifier }}'
      PropertySelector: '$.DBInstances[0].DBInstanceStatus'
      DesiredValues:
        - available

  - name: InvokeRegisterLambda
    action: aws:invokeLambdaFunction
    inputs:
      FunctionName: '{{ LambdaFunctionName }}'
      Payload: >-
        {
          "DBInstanceIdentifier": "{{ DBInstanceIdentifier }}",
          "InvokedBy": "SSMAutomationDocument"
        }
YAML
}