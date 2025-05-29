tf-rds-failover-automation/
├── main.tf                     # Core resource definitions
├── variables.tf                # Input variables
├── outputs.tf                  # Output values
├── iam.tf                      # IAM roles and policies
├── lambda.tf                   # Lambda function and related resources
├── ssm.tf                      # SSM Document
├── lambda_code/                # Directory for Lambda function code
│   └── register_targets.py
└── README.md                   # Instructions on how to use the module

# Terraform RDS Failover Automation Module

This module creates the necessary AWS resources to automate an RDS failover process, including:
1.  Forcing an RDS DB instance failover.
2.  Updating a Security Group to allow access from new DR instances (IPs provided as parameters).
3.  Waiting for the RDS instance to become available after failover.
4.  Invoking a Lambda function to register new EC2 instances with specified Target Groups and deregister old ones.

## Resources Created

*   **IAM Role for SSM Automation**: Role assumed by the SSM Automation document.
*   **IAM Role for Lambda Execution**: Role assumed by the Lambda function.
*   **Lambda Function**: Python function to register/deregister EC2 instances with ELB Target Groups.
*   **SSM Automation Document**: The document defining the failover steps.

## Usage

```hcl
module "rds_failover_automation" {
  source = "./tf-rds-failover-automation" # Or path to your module

  db_instance_identifier    = "my-rds-instance"
  target_group_ui_arn       = "arn:aws:elasticloadbalancing:region:account-id:targetgroup/my-ui-tg/id"
  target_group_tomcat_arn   = "arn:aws:elasticloadbalancing:region:account-id:targetgroup/my-tomcat-tg/id"
  target_group_tokengen_arn = "arn:aws:elasticloadbalancing:region:account-id:targetgroup/my-tokengen-tg/id"

  new_ec2_instance_ids = "i-newinstance1,i-newinstance2"
  old_ec2_instance_ids = "i-oldinstance1,i-oldinstance2"

  # Override default names if needed
  # ssm_automation_role_name   = "MyCustomSSMAutomationRole"
  # lambda_function_name       = "MyCustomLambdaFunction"
  # ssm_document_name          = "MyCustomSSMDocument"

  # --- IMPORTANT: Provide these values specific to your environment ---
  target_security_group_id = "sg-xxxxxxxxxxxxxxxxx" # SG attached to your RDS instance
  dr_instance_1_cidr_ip    = "10.0.1.10/32"         # CIDR of your DR App Instance 1
  dr_instance_2_cidr_ip    = "10.0.2.20/32"         # CIDR of your DR App Instance 2

  tags = {
    Environment = "DR"
    Project     = "FailoverAutomation"
  }
}
