# my-dr-orchestration/variables.tf

variable "aws_region" {
  description = "AWS region to deploy resources."
  type        = string
  default     = "ap-south-1"
}

variable "environment_tag" {
  description = "Tag to identify the environment (e.g., dr, prod, dev)."
  type        = string
  default     = "dr-testing"
}

variable "project_tag" {
  description = "Tag to identify the project."
  type        = string
  default     = "RDSFailoverAutomation"
}

# --- Variables for the rds_failover_automation module ---

variable "rds_db_instance_identifier" {
  type        = string
  description = "RDS DB instance identifier for failover."
  default     = "dr-failover-cfn-test-tf" # Example, please change
}

variable "alb_target_group_ui_arn" {
  type        = string
  description = "ARN of the UI Target Group."
  # Example ARN - replace with your actual ARN
  default = "arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/My-UI-TG/abcdef1234567890"
}

variable "alb_target_group_tomcat_arn" {
  type        = string
  description = "ARN of the Tomcat Target Group."
  # Example ARN - replace with your actual ARN
  default = "arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/My-Tomcat-TG/1234567890abcdef"
}

variable "alb_target_group_tokengen_arn" {
  type        = string
  description = "ARN of the Tokengen Target Group."
  # Example ARN - replace with your actual ARN
  default = "arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/My-Tokengen-TG/fedcba0987654321"
}

variable "new_dr_ec2_instance_ids" {
  type        = string
  description = "Comma-separated list of new EC2 instance IDs in the DR site."
  default     = "i-0123456789abcdef0,i-0fedcba9876543210" # Example, please change
}

variable "old_dc_ec2_instance_ids" {
  type        = string
  description = "Comma-separated list of old EC2 instance IDs in the DC site."
  default     = "i-0abcdef0123456789,i-09876543210fedcba" # Example, please change
}

variable "rds_security_group_id" {
  type        = string
  description = "The Security Group ID attached to your RDS instance that needs ingress rules."
  # Example SG ID - replace with your actual SG ID
  default = "sg-0123456789abcdef0"
}

variable "dr_app_instance_1_cidr_ip" {
  type        = string
  description = "CIDR IP for the first DR application instance to allow DB access (e.g., 10.0.1.10/32)."
  # Example IP - replace with your actual IP
  default = "172.31.5.10/32"
}

variable "dr_app_instance_2_cidr_ip" {
  type        = string
  description = "CIDR IP for the second DR application instance to allow DB access (e.g., 10.0.2.20/32)."
  # Example IP - replace with your actual IP
  default = "172.31.6.20/32"
}