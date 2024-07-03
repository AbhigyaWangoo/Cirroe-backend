from typing import Any, Tuple, List
import json
import boto3
from . import base

from src.model.stack import CloudFormationStack
from src.db.supa import SupaClient, ChatSessionState

from include.utils import prompt_with_file, BASE_PROMPT_PATH
from enum import Enum

# TODO use this to validate whether a stack is valid or not before deployment: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/client/validate_template.html

NUM_RETRIES = 3
REQUEST_DEPLOYMENT_INFO_PROMPT = "request_deployment_info.txt"

# Ret messages
REDPLOYMENT_RESPONSE = "Looks like you already have attempted to deploy this infra before. Try opening up a new one."
WIP_RESPONSE = "Hang tight, the deployment is still happening. Check back later."
SUCCESS_RESPONSE = "Huzzah, your deployment succeeded! You can take it from here, please let me know if you have any additional questions regarding the deployment!"
NO_INPUT_YET_RESPONSE = "I don't think you've given me any specifications yet. Pls provide some before you deploy."
ERROR_RESPONSE = (
    "Awe man, looks like something failed with the deployment. Please contact support."
)


class DiagnoserState(Enum):
    """
    Represents whether or not the stack is ready for deployment
    """

    DEPLOYABLE = 0
    INACCURATE_OR_MISSING_INFORMATION = 1
    INVALID_FORMAT = 2
    OTHER = 3


class Diagnoser:
    """
    A class that intakes a cf stack, and diagnoses what is or isn't wrong with the template.
    """

    def __init__(
        self, stack: CloudFormationStack, cf_client: boto3.session.Session.client
    ) -> None:
        self.stack = stack
        self.cf_client = cf_client

    def fix_broken_stack(
        self, diagnosed_issue: DiagnoserState | None
    ) -> CloudFormationStack:
        """
        A helper fn to fix a broken stack. Assumes that the provided stack is broken as is.
        Returns the fixed stack.
        """

        # if hallucination on logic or vars, do CoV retries
        # if missing info, return msg asking for missing info

        return self.stack

    def determine_stack_deployability(
        self, current_state: ChatSessionState
    ) -> DiagnoserState:
        """
        A binary classifier that returns whether the stack can be deployed or not.
        """
        # If the stack has been deployed before, check logs to see for failures. If there are logs, return missing state.
        # Skipping invalid format for now. Expecting that will be handled by retries
        if current_state == ChatSessionState.DEPLOYMENT_FAILED and self.get_stack_logs(
            self.stack.name
        ):
            return DiagnoserState.INACCURATE_OR_MISSING_INFORMATION
        elif (
            current_state == ChatSessionState.DEPLOYMENT_SUCCEEDED
            or current_state == ChatSessionState.QUERIED_AND_DEPLOYABLE
        ):
            return DiagnoserState.DEPLOYABLE

        return DiagnoserState.OTHER

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

        self.state_manager.update_chat_session_state(
            self.chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
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
            try:
                # Check if the stack exists
                existing_stacks = self.cf_client.describe_stacks(StackName=stack_name)
                stack_exists = any(
                    stack["StackName"] == stack_name
                    for stack in existing_stacks["Stacks"]
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

            print("Waiting on stack deployment...")
            waiter.wait(StackName=stack_name)
            print(f"Stack {stack_name} deployment complete.")
            state = ChatSessionState.DEPLOYMENT_SUCCEEDED
        except Exception as e:
            print(f"Error during stack deployment: {e}")
            state = ChatSessionState.DEPLOYMENT_FAILED
        finally:
            self.state_manager.update_chat_session_state(self.chat_session_id, state)

        if (
            state == ChatSessionState.DEPLOYMENT_FAILED
        ):  # if deployment failed, clean the resources
            response = self.cf_client.delete_stack(StackName=stack_name)

            # Wait until the stack deletion is complete
            waiter = self.cf_client.get_waiter("stack_delete_complete")
            print(f"Deleting stack {stack_name}...")
            waiter.wait(StackName=stack_name)
            print(f"Stack {stack_name} has been deleted.")

        return str(response), state

    def handle_failed_deployment(
        self, diagnoser: Diagnoser, diagnosed_issue: DiagnoserState | None = None
    ) -> str:
        """
        Handles a failed deployment with the Diagnoser class.
        Returns a message to the user
        """
        new_stack = diagnoser.fix_broken_stack(diagnosed_issue)

        for _ in range(NUM_RETRIES):
            _, state = self.deploy_stack(new_stack.name)

            if state == ChatSessionState.DEPLOYMENT_SUCCEEDED:
                return SUCCESS_RESPONSE

        return ERROR_RESPONSE

    def trigger_action(self) -> Any:
        """
        Entrypoint for deploying a stack to aws
        """

        state = self.state_manager.get_chat_session_state(self.chat_session_id)
        response = ""

        #   1.a If previously deployed, check state.
        if state == ChatSessionState.DEPLOYMENT_SUCCEEDED:
            # 1.b If succeeded, return msg saying we don't do redeployments
            response = REDPLOYMENT_RESPONSE
        elif state == ChatSessionState.DEPLOYMENT_IN_PROGRESS:
            # 1.c If in progress, return msg saying a deployment is in progress
            response = WIP_RESPONSE
        elif state == ChatSessionState.DEPLOYMENT_FAILED:
            response = self.handle_failed_deployment(
                Diagnoser(self.user_stack, self.cf_client)
            )
        elif state == ChatSessionState.QUERIED_AND_DEPLOYABLE:
            response, state = self.deploy_stack(
                input
            )  # 1.e If deployable but not deployed, run deployment.
        elif (
            state == ChatSessionState.QUERIED
            or state == ChatSessionState.QUERIED_NOT_DEPLOYABLE
        ):
            diagnoser = Diagnoser(
                self.user_stack, self.cf_client
            )  # 2. if never deployed, validate stack is deployable
            diagnoser_decision = diagnoser.determine_stack_deployability(state)

            #   2.a if not deployable, call diagnoser with same retry/missing info requests
            if diagnoser_decision == DiagnoserState.DEPLOYABLE:
                response, state = self.deploy_stack(
                    input
                )  # 2.b if deployable, attempt deployment.
                if state == ChatSessionState.DEPLOYMENT_SUCCEEDED:
                    # 2.b.1 if succeeded, return msg saying deployment succeeded
                    response = SUCCESS_RESPONSE
                else:
                    response = self.handle_failed_deployment(
                        diagnoser, diagnoser_decision
                    )  # 2.b.2 if failed, call diagnoser with same retry/missing info requests
            else:
                response = self.handle_failed_deployment(
                    diagnoser, diagnoser_decision
                )  # 2.b.2 if failed, call diagnoser with same retry/missing info requests
        elif state == ChatSessionState.NOT_QUERIED:
            # return msg saying you haven't given me any specs. what am i supposed to do lol.
            response = NO_INPUT_YET_RESPONSE
        elif state == ChatSessionState.DEPLOYMENT_FAILED:
            # return some kind of error message to the user
            pass

        return response
