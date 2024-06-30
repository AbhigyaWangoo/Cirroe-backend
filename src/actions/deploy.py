from typing import Any
import json
import boto3
from . import base

from src.model.stack import CloudFormationStack

# TODO use this to validate whether a stack is valid or not before deployment: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/client/validate_template.html

# Deployment should go as follows
# 1. Lint the deployment.
#       If not passing, return reasons for what needs to be fixed
#       If passing, attempt to deploy
#           If deployment fails, see if there is info needed from user or not. If yes, request from user. if no, break gracefully.


class DeployCFStackAction(base.AbstractAction):
    """
    An action to deploy a cf stack to a user's account
    """

    def __init__(
        self,
        user_stack: CloudFormationStack,
        user_aws_secret_key: str,
        user_aws_access_key_id: str,
    ) -> None:
        """
        Constructs a user deployment action
        """
        self.user_secret_key = user_aws_secret_key
        self.user_aws_access_key_id = user_aws_access_key_id

        self.cf_client = boto3.client(
            "cloudformation",
            aws_access_key_id=self.user_aws_access_key_id,
            aws_secret_access_key=self.user_secret_key,
        )

        self.user_stack = user_stack
        super().__init__()

    def trigger_action(self, input) -> Any:
        """
        Deploys user's cf stack into their account
        """

        stack_name = input
        template_body = json.dumps(self.user_stack.template)
        stack_exists = True

        try:
            # Check if the stack exists
            existing_stacks = self.cf_client.describe_stacks(StackName=stack_name)
            stack_exists = any(
                stack["StackName"] == stack_name for stack in existing_stacks["Stacks"]
            )
        except self.cf_client.exceptions.ClientError as e:
            if "does not exist" in str(e):
                stack_exists = False
            else:
                raise

        if stack_exists:
            # Update the stack
            print(f"Updating stack {stack_name}...")
            response = self.cf_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )
        else:
            # Create the stack
            print(f"Creating stack {stack_name}...")
            response = self.cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )

        # Wait for the stack to be created/updated
        waiter = self.cf_client.get_waiter(
            "stack_create_complete" if not stack_exists else "stack_update_complete"
        )
        try:
            waiter.wait(StackName=stack_name)
            print(f"Stack {stack_name} deployment complete.")
        except Exception as e:
            print(f"Error waiting for stack deployment: {e}")

        return response
