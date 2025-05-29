# tf-rds-failover-automation/iam.tf

# IAM Role for SSM Automation
resource "aws_iam_role" "ssm_automation_role" {
  name               = var.ssm_automation_role_name
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "ssm.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "ssm_automation_policy" {
  name = "AllowRDS-EC2-Lambda-SSM"
  role = aws_iam_role.ssm_automation_role.id
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "rds:RebootDBInstance",
          "ec2:AuthorizeSecurityGroupIngress",
          "rds:DescribeDBInstances",
          "lambda:InvokeFunction"
        ],
        Resource = "*" # Consider scoping this down if possible
      }
    ]
  })
}

# IAM Role for Lambda Function
resource "aws_iam_role" "lambda_execution_role" {
  name               = var.lambda_execution_role_name
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "lambda_register_targets_policy" {
  name = "RegisterDeregisterTargetsPolicy"
  role = aws_iam_role.lambda_execution_role.id
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "elasticloadbalancing:RegisterTargets",
          "elasticloadbalancing:DeregisterTargets"
        ],
        Resource = "*" # Consider scoping this to specific target group ARNs
      },
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*" # Standard Lambda logging permissions
      }
    ]
  })
}
