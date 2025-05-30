# tf-rds-failover-automation/lambda.tf

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_code/"
  output_path = "${path.module}/lambda_code/register_targets.zip"
}

resource "aws_lambda_function" "register_targets_lambda" {
  function_name    = var.lambda_function_name
  handler          = "register_targets.handler" # Corresponds to filename.handler_function
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_execution_role.arn
  timeout          = 60
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      TG_UI_ARN         = var.target_group_ui_arn
      TG_TOMCAT_ARN     = var.target_group_tomcat_arn
      TG_TOKENGEN_ARN   = var.target_group_tokengen_arn
      NEW_INSTANCES_IDS = var.new_ec2_instance_ids
      OLD_INSTANCES_IDS = var.old_ec2_instance_ids
    }
  }
  tags = var.tags

  # Ensure roles are created before lambda
  depends_on = [
    aws_iam_role.lambda_execution_role,
    aws_iam_role_policy.lambda_register_targets_policy
  ]
}