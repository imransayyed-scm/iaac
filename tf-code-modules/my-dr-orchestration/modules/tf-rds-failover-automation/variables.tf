# tf-rds-failover-automation/variables.tf

variable "db_instance_identifier" {
  type        = string
  description = "RDS DB instance identifier"
  default     = "dr-failover-cfn-test"
}

variable "target_group_ui_arn" {
  type        = string
  description = "ARN of the UI Target Group"
  default     = "arn:aws:elasticloadbalancing:ap-south-1:467660529422:targetgroup/Posidex-DC-DR-UI-Test-TG/4c14bd8b597d3c33"
}

variable "target_group_tomcat_arn" {
  type        = string
  description = "ARN of the Tomcat Target Group"
  default     = "arn:aws:elasticloadbalancing:ap-south-1:467660529422:targetgroup/Posidex-DC-DR-Tomcat-Test-TG/d6c5c09915e2a791"
}

variable "target_group_tokengen_arn" {
  type        = string
  description = "ARN of the Tokengen Target Group"
  default     = "arn:aws:elasticloadbalancing:ap-south-1:467660529422:targetgroup/Posidex-DC-DR-Tokengen-Test-TG/57d9afda9a9c0fbe"
}

variable "new_ec2_instance_ids" {
  type        = string # Keeping as string to match Lambda's expectation of comma-separated
  description = "Comma-separated list of new EC2 instance IDs"
  default     = "i-06956b6ce7039d983,i-0a08e5fcab036c1e5"
}

variable "old_ec2_instance_ids" {
  type        = string # Keeping as string
  description = "Comma-separated list of old EC2 instance IDs"
  default     = "i-06956b6ce7039d983,i-0a08e5fcab036c1e5"
}

variable "ssm_automation_role_name" {
  type        = string
  description = "Name for the SSM Automation IAM Role"
  default     = "SSM-RDS-Failover-AutomationRole"
}

variable "lambda_execution_role_name" {
  type        = string
  description = "Name for the Lambda Execution IAM Role"
  default     = "RegisterTargetsLambdaExecutionRole"
}

variable "lambda_function_name" {
  type        = string
  description = "Name for the Lambda function"
  default     = "RegisterTargetsAfterRDSAvailable"
}

variable "ssm_document_name" {
  type        = string
  description = "Name for the SSM Automation Document"
  default     = "RDS-Force-Failover"
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to created resources."
  default     = {}
}

# Variables for hardcoded values in SSM document (making them configurable)
variable "target_security_group_id" {
  type        = string
  description = "The Security Group ID to authorize ingress for RDS."
  default     = "sg-01fe63d5cf1d626e9" # Default from CFN, should be changed
}

variable "dr_instance_1_cidr_ip" {
  type        = string
  description = "CIDR IP for DR instance 1 to allow DB access."
  default     = "172.28.7.144/32" # Default from CFN, should be changed
}

variable "dr_instance_2_cidr_ip" {
  type        = string
  description = "CIDR IP for DR instance 2 to allow DB access."
  default     = "172.28.7.181/32" # Default from CFN, should be changed
}