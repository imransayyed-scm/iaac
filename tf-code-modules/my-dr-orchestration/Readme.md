Ensure you have the tf-rds-failover-automation module directory correctly placed (e.g., inside my-dr-orchestration/modules/).
Navigate to the my-dr-orchestration directory in your terminal.
Modify my-dr-orchestration/variables.tf or create a terraform.tfvars file in the my-dr-orchestration directory to provide your specific values for ARNs, instance IDs, security group IDs, and CIDR IPs.
Example my-dr-orchestration/terraform.tfvars

aws_region                      = "ap-south-1"
rds_db_instance_identifier    = "my-actual-rds-instance"
alb_target_group_ui_arn       = "arn:aws:elasticloadbalancing:ap-south-1:ACCOUNTID:targetgroup/Prod-UI-TG/..."
alb_target_group_tomcat_arn   = "arn:aws:elasticloadbalancing:ap-south-1:ACCOUNTID:targetgroup/Prod-Tomcat-TG/..."
alb_target_group_tokengen_arn = "arn:aws:elasticloadbalancing:ap-south-1:ACCOUNTID:targetgroup/Prod-Tokengen-TG/..."
new_dr_ec2_instance_ids       = "i-drInstance1,i-drInstance2"
old_dc_ec2_instance_ids       = "i-dcInstance1,i-dcInstance2"
rds_security_group_id         = "sg-actualrdssecgroupid"
dr_app_instance_1_cidr_ip     = "10.100.1.5/32"
dr_app_instance_2_cidr_ip     = "10.100.2.5/32"

Initialize Terraform: 
terraform init
Review the plan: 
terraform plan (or terraform plan -var-file=terraform.tfvars if you used that)
Apply the configuration: 
terraform apply (or terraform apply -var-file=terraform.tfvars)
This setup provides a clean separation of concerns, with the reusable logic encapsulated in the tf-rds-failover-automation module and the environment-specific configuration handled by the root module (my-dr-orchestration).