from typing import Any, Tuple, List
import json
import boto3
from . import base

from src.model.stack import CloudFormationStack
from src.db.supa import SupaClient, ChatSessionState

from include.utils import prompt_with_file, BASE_PROMPT_PATH
from enum import Enum

# TODO use this to validate whether a stack is valid or not before deployment: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/client/validate_template.html

# Deployment should go as follows
# 1. Lint the deployment.
#       If not passing, return reasons for what needs to be fixed
#       If passing, attempt to deploy
#           If deployment fails, see if there is info needed from user or not. If yes, request from user. if no, break gracefully.

REQUEST_DEPLOYMENT_INFO_PROMPT = "request_deployment_info.txt"


class DeployableState(Enum):
    """
    Represents whether or not the stack is ready for deployment
    """

    DEPLOYABLE = 0
    INACCURACTE_INFORMATION = 1
    MISSING_INFORMATION = 2
    INVALID_FORMAT = 3
    OTHER = 4


class DeployCFStackAction(base.AbstractAction):
    """
    An action to deploy a cf stack to a user's account
    """

    def __init__(
        self,
        user_stack: CloudFormationStack,
        chat_session_id: int,
        state_manager: SupaClient,
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
        self.state_manager = state_manager
        self.chat_session_id = chat_session_id
        super().__init__()

    def verify_stack_deployable(self) -> DeployableState:
        """
        A binary classifier that returns whether the stack can be deployed or not.
        """
        # If the stack has been deployed before, check logs to see for failures

        # If not, check cf stack with gpt call to check if it has issues. If no issues, return true.
        return True

    def get_stack_logs(self, stack_name: str) -> List[str]:
        """
        Get logs for a cf stack deployment. Returns a list of log messages.
        """

        # Get stack events
        response = self.cf_client.describe_stack_events(StackName=stack_name)

        # Print out the events
        logs = []
        for event in response["StackEvents"]:
            if "FAILED" in event["ResourceStatus"]:
                logs.append(
                    f"""
                    Resource: {event['LogicalResourceId']}
                    Status: {event['ResourceStatus']}
                    Reason: {event['ResourceStatusReason']}
                """
                )

        return logs

    def request_deployment_info(self) -> str:
        """
        Coalesce a response to the user requesting the remaining info for a deployment.
        Consider's the user's input as well.
        """

        prompt = f"""
            cloudformation stack template:
            {json.dumps(self.user_stack.template)}
        """

        response = prompt_with_file(
            BASE_PROMPT_PATH + REQUEST_DEPLOYMENT_INFO_PROMPT, prompt, self.gpt_client
        )

        return response

    def deploy_stack(self, stack_name: str) -> Tuple[str, ChatSessionState]:
        """
        Deploys user's cf stack into their account
        """

        template_body = json.dumps(self.user_stack.template)
        stack_exists = True
        state: ChatSessionState
        response = None

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
            print(f"Updating stack {stack_name}")
            response = self.cf_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )
        else:
            # Create the stack
            print(f"Creating stack {stack_name}")
            response = self.cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )

        # Marking the deployment as in progress
        state = ChatSessionState.DEPLOYMENT_IN_PROGRESS
        self.state_manager.update_chat_session_state(
            self.chat_session_id, ChatSessionState.DEPLOYMENT_IN_PROGRESS
        )

        # Wait for the stack to be created/updated
        waiter = self.cf_client.get_waiter(
            "stack_create_complete" if not stack_exists else "stack_update_complete"
        )
        try:
            print("Waiting on stack deployment...")
            waiter.wait(StackName=stack_name)
            print(f"Stack {stack_name} deployment complete.")
            state = ChatSessionState.DEPLOYMENT_SUCCEEDED
        except Exception as e:
            print(f"Error waiting for stack deployment: {e}")
            state = ChatSessionState.DEPLOYMENT_FAILED
            return str(e)
        finally:
            self.state_manager.update_chat_session_state(self.chat_session_id, state)

        return str(response)

    def trigger_action(self, input) -> Any:
        """
        Entrypoint for deploying a stack to aws
        """

        # 1. Check Whether stack can be deployed, according to a previous run. If it
        # wasn't then check right now to see deployability.
        state = self.state_manager.get_cf_stack(self.chat_session_id)
        deployable = state == ChatSessionState.QUERIED_AND_DEPLOYABLE
        deployment_state: DeployableState
        if not deployable:
            deployment_state = self.verify_stack_deployable()

        # 2. if yes, deploy it. Return a deployment report to the user.
        if deployment_state == DeployableState.DEPLOYABLE:
            return self.deploy_stack(input)
        elif deployment_state == DeployableState.INVALID_FORMAT:
            # Output format was a json
            pass
        elif deployment_state == DeployableState.INACCURACTE_INFORMATION:
            # LLM hallucinated info (ami id, login creds)
            pass
        elif deployment_state == DeployableState.MISSING_INFORMATION:
            # Request more info from user.
            pass
        elif deployment_state == DeployableState.OTHER:
            # throw error
            pass

        # 3. if no, send msg to user asking for remaining info.
        pass
