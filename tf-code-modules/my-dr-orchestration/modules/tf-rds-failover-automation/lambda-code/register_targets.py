# tf-rds-failover-automation/lambda_code/register_targets.py

import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    elbv2 = boto3.client('elbv2')

    tg_ui_arn = os.environ.get('TG_UI_ARN')
    tg_tomcat_arn = os.environ.get('TG_TOMCAT_ARN')
    tg_tokengen_arn = os.environ.get('TG_TOKENGEN_ARN')
    new_instances_str = os.environ.get('NEW_INSTANCES_IDS', "")
    old_instances_str = os.environ.get('OLD_INSTANCES_IDS', "")

    if not all([tg_ui_arn, tg_tomcat_arn, tg_tokengen_arn, new_instances_str, old_instances_str]):
        logger.error("Missing one or more environment variables: TG_UI_ARN, TG_TOMCAT_ARN, TG_TOKENGEN_ARN, NEW_INSTANCES_IDS, OLD_INSTANCES_IDS")
        return {"status": "error", "message": "Missing environment variables"}

    new_instances = [i.strip() for i in new_instances_str.split(',') if i.strip()]
    old_instances = [i.strip() for i in old_instances_str.split(',') if i.strip()]

    actions = []

    try:
        # --- Register New Targets ---
        # Assuming specific instance mappings and ports as per original CFN
        # UI TG: First new instance, port 8089
        if len(new_instances) >= 1:
            logger.info(f"Registering {new_instances[0]}:8089 to UI TG: {tg_ui_arn}")
            elbv2.register_targets(TargetGroupArn=tg_ui_arn, Targets=[{'Id': new_instances[0], 'Port': 8089}])
            actions.append(f"Registered {new_instances[0]} to UI TG")

        # Tomcat TG: First and second new instances, port 8089
        if len(new_instances) >= 2:
            tomcat_targets = [{'Id': new_instances[0], 'Port': 8089}, {'Id': new_instances[1], 'Port': 8089}]
            logger.info(f"Registering {tomcat_targets} to Tomcat TG: {tg_tomcat_arn}")
            elbv2.register_targets(TargetGroupArn=tg_tomcat_arn, Targets=tomcat_targets)
            actions.append(f"Registered {new_instances[0]},{new_instances[1]} to Tomcat TG")
        elif len(new_instances) == 1: # Handle case if only one new instance provided for Tomcat
            tomcat_targets = [{'Id': new_instances[0], 'Port': 8089}]
            logger.info(f"Registering {tomcat_targets} to Tomcat TG: {tg_tomcat_arn} (only one instance available)")
            elbv2.register_targets(TargetGroupArn=tg_tomcat_arn, Targets=tomcat_targets)
            actions.append(f"Registered {new_instances[0]} to Tomcat TG")


        # Tokengen TG: First new instance, port 2405
        if len(new_instances) >= 1:
            logger.info(f"Registering {new_instances[0]}:2405 to Tokengen TG: {tg_tokengen_arn}")
            elbv2.register_targets(TargetGroupArn=tg_tokengen_arn, Targets=[{'Id': new_instances[0], 'Port': 2405}])
            actions.append(f"Registered {new_instances[0]} to Tokengen TG")

        # --- Deregister Old Targets ---
        # UI TG: First old instance, port 8089
        if len(old_instances) >= 1:
            logger.info(f"Deregistering {old_instances[0]}:8089 from UI TG: {tg_ui_arn}")
            elbv2.deregister_targets(TargetGroupArn=tg_ui_arn, Targets=[{'Id': old_instances[0], 'Port': 8089}])
            actions.append(f"Deregistered {old_instances[0]} from UI TG")

        # Tomcat TG: First and second old instances, port 8089
        if len(old_instances) >= 2:
            tomcat_targets_old = [{'Id': old_instances[0], 'Port': 8089}, {'Id': old_instances[1], 'Port': 8089}]
            logger.info(f"Deregistering {tomcat_targets_old} from Tomcat TG: {tg_tomcat_arn}")
            elbv2.deregister_targets(TargetGroupArn=tg_tomcat_arn, Targets=tomcat_targets_old)
            actions.append(f"Deregistered {old_instances[0]},{old_instances[1]} from Tomcat TG")
        elif len(old_instances) == 1: # Handle case if only one old instance provided for Tomcat
            tomcat_targets_old = [{'Id': old_instances[0], 'Port': 8089}]
            logger.info(f"Deregistering {tomcat_targets_old} from Tomcat TG: {tg_tomcat_arn} (only one instance available)")
            elbv2.deregister_targets(TargetGroupArn=tg_tomcat_arn, Targets=tomcat_targets_old)
            actions.append(f"Deregistered {old_instances[0]} from Tomcat TG")

        # Tokengen TG: First old instance, port 2405
        if len(old_instances) >= 1:
            logger.info(f"Deregistering {old_instances[0]}:2405 from Tokengen TG: {tg_tokengen_arn}")
            elbv2.deregister_targets(TargetGroupArn=tg_tokengen_arn, Targets=[{'Id': old_instances[0], 'Port': 2405}])
            actions.append(f"Deregistered {old_instances[0]} from Tokengen TG")

        logger.info(f"Actions completed: {actions}")
        return {"status": "targets updated", "actions": actions}

    except Exception as e:
        logger.error(f"Error processing targets: {str(e)}")
        return {"status": "error", "message": str(e)}