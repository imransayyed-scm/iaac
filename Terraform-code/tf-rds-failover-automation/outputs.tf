# tf-rds-failover-automation/outputs.tf

output "ssm_document_name" {
  description = "The name of the created SSM Automation Document."
  value       = aws_ssm_document.rds_failover_document.name
}

output "ssm_document_arn" {
  description = "The ARN of the created SSM Automation Document."
  value       = aws_ssm_document.rds_failover_document.arn
}

output "ssm_automation_role_arn" {
  description = "The ARN of the IAM role for SSM Automation."
  value       = aws_iam_role.ssm_automation_role.arn
}

output "lambda_function_name" {
  description = "The name of the Lambda function."
  value       = aws_lambda_function.register_targets_lambda.function_name
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda function."
  value       = aws_lambda_function.register_targets_lambda.arn
}

output "lambda_execution_role_arn" {
  description = "The ARN of the IAM role for Lambda execution."
  value       = aws_iam_role.lambda_execution_role.arn
}
