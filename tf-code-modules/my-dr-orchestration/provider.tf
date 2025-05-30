# my-dr-orchestration/provider.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # Specify a version constraint
    }
    archive = { # Needed for zipping the Lambda code
      source  = "hashicorp/archive"
      version = "~> 2.2"
    }
  }

  # Optional: Backend configuration for storing Terraform state remotely
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket-name"
  #   key            = "dr-orchestration/terraform.tfstate"
  #   region         = "ap-south-1"
  #   encrypt        = true
  #   # dynamodb_table = "your-terraform-state-lock-table" # For state locking
  # }
}

provider "aws" {
  region = var.aws_region
  # profile = "your-aws-profile" # Optional: if using a specific AWS CLI profile
  # access_key = var.aws_access_key # Optional: Not recommended for production
  # secret_key = var.aws_secret_key # Optional: Not recommended for production
}