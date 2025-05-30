# my-dr-orchestration/main.tf

locals {
  common_tags = {
    Environment = var.environment_tag
    Project     = var.project_tag
    Terraform   = "true"
    ManagedBy   = "Terraform-Root-Module"
  }
}

module "rds_failover_automation_orchestrator" {
  # If the module is local, use a relative path:
  source = "./modules/tf-rds-failover-automation"
  # If the module is in a Git repository:
  # source = "git::https://github.com/your-repo/tf-rds-failover-automation.git?ref=v1.0.0"
  # If the module is in the Terraform Registry:
  # source  = "your-namespace/rds-failover-automation/aws"
  # version = "1.0.0"

  # --- Pass values from root module variables to the child module ---
  db_instance_identifier    = var.rds_db_instance_identifier
  target_group_ui_arn       = var.alb_target_group_ui_arn
  target_group_tomcat_arn   = var.alb_target_group_tomcat_arn
  target_group_tokengen_arn = var.alb_target_group_tokengen_arn

  new_ec2_instance_ids      = var.new_dr_ec2_instance_ids
  old_ec2_instance_ids      = var.old_dc_ec2_instance_ids

  # These parameters are for the SSM document and are critical
  target_security_group_id  = var.rds_security_group_id
  dr_instance_1_cidr_ip     = var.dr_app_instance_1_cidr_ip
  dr_instance_2_cidr_ip     = var.dr_app_instance_2_cidr_ip

  # You can also override default names from the child module if needed
  # ssm_automation_role_name   = "CustomSSMAutomationRole-${var.environment_tag}"
  # lambda_function_name       = "CustomRegisterTargetsLambda-${var.environment_tag}"
  # ssm_document_name          = "CustomRDSForceFailover-${var.environment_tag}"

  tags = local.common_tags
}