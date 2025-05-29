# iaac
🏗️ Infrastructure as Code (IaC) for AWS – CloudFormation & Terraform
This repository contains Infrastructure as Code (IaC) templates and modules for provisioning and managing AWS resources using CloudFormation (CFN) and Terraform.

🔧 What’s Included:
CloudFormation templates for deploying AWS infrastructure in a declarative manner
Terraform modules and configurations for reusable, scalable deployments
Environment-specific configurations (dev, test, prod)
Scripts and automation to simplify deployment and testing

📌 Purpose:
To provide a centralized, version-controlled collection of IaC assets to streamline AWS infrastructure provisioning and ensure consistency, repeatability, and best practices across environments.

/cfn/
  ├── vpc.yaml
  ├── ec2.yaml
  └── ...
/terraform/
  ├── modules/
  ├── environments/
  └── main.tf
/scripts/
README.md

🚀 Getting Started:
Refer to the README in each subdirectory for setup instructions and usage examples.

**Prerequisites:**
AWS CLI configured with appropriate credentials
Terraform installed (version X.X or higher)
Necessary IAM permissions for resource creation

**Deploying CloudFormation:**
aws cloudformation deploy --template-file cfn/vpc.yaml --stack-name my-vpc-stack --parameter-overrides Key=Value

**Using Terraform:**
cd terraform/environments/dev
terraform init
terraform plan
terraform apply

**Contributing**
Feel free to submit issues or pull requests for improvements, bug fixes, or additional modules.
