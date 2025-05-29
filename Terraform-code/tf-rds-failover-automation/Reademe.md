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

aws ssm start-automation-execution \
    --document-name "RDS-Force-Failover" --parameters "DBInstanceIdentifier=your-rds-id,AutomationAssumeRole=arn:aws:iam::YOUR_ACCOUNT_ID:role/SSM-RDS-Failover-AutomationRole,
    --region your-aws-region
