# my-dr-orchestration/outputs.tf

output "automation_ssm_document_name" {
  description = "The name of the created SSM Automation Document."
  value       = module.rds_failover_automation_orchestrator.ssm_document_name
}

output "automation_ssm_document_arn" {
  description = "The ARN of the created SSM Automation Document."
  value       = module.rds_failover_automation_orchestrator.ssm_document_arn
}

output "automation_ssm_role_arn" {
  description = "The ARN of the IAM role for SSM Automation execution."
  value       = module.rds_failover_automation_orchestrator.ssm_automation_role_arn
}

output "automation_lambda_function_name" {
  description = "The name of the Lambda function for target registration."
  value       = module.rds_failover_automation_orchestrator.lambda_function_name
}

output "automation_lambda_function_arn" {
  description = "The ARN of the Lambda function."
  value       = module.rds_failover_automation_orchestrator.lambda_function_arn
}