from typing import Any, Tuple, List
import json
from uuid import UUID
from python_terraform import *
from . import base
from collections import deque

from src.model.stack import TerraformConfig
from src.db.supa import SupaClient, ChatSessionState

from include.llm.base import AbstractLLMClient
from include.utils import prompt_with_file, BASE_PROMPT_PATH
from enum import Enum

# TODO use this to validate whether a stack is valid or not before deployment: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/client/validate_template.html

NUM_RETRIES = 1
LOG_LIMIT = 100

REQUEST_DEPLOYMENT_INFO_PROMPT = "request_deployment_info.txt"
VERIFY_CONSTRUCTED_CONFIG = "verify_config.txt"

# Ret messages
REDPLOYMENT_RESPONSE = "Looks like you already have attempted to deploy this infra before. Try opening up a new one."
WIP_RESPONSE = "Hang tight, the deployment is still happening. Check back later."
SUCCESS_RESPONSE = "Huzzah, your deployment succeeded! You can take it from here, please let me know if you have any additional questions regarding the deployment!"
NO_INPUT_YET_RESPONSE = "I don't think you've given me any specifications yet. Pls provide some before you deploy."
ERROR_RESPONSE = (
    "Awe man, looks like something failed with the deployment. Please contact support."
)
DESTROY_SUCCESS = "Successfully destroyed and cleaned up your resources."


class DiagnoserState(Enum):
    """
    Represents whether or not the config is ready for deployment
    """

    DEPLOYABLE = 0
    MISSING_OR_INVALID_DATA = 1
    OTHER = 2


class TFConfigRequiresUserInfoException(Exception):
    """
    An exception that marks cases where configs cannot be fixed in any capacity
    """

    pass


class DeploymentBrokenException(Exception):
    """
    An exception that marks cases where a broken deployment can't be debugged.
    """

    pass


class Diagnoser:
    """
    A class that intakes a tf config, and diagnoses what is or isn't wrong with the template.
    """

    def __init__(
        self,
        config: TerraformConfig,
        llm_client: AbstractLLMClient,
        log_cache_limit=LOG_LIMIT,
    ) -> None:
        self.config = config
        self.logs_cache = deque(maxlen=log_cache_limit)
        self.llm_client = llm_client

    def fix_broken_config(self, diagnosed_issue: DiagnoserState) -> TerraformConfig:
        """
        A helper fn to fix a broken config. Assumes that the provided config is broken as is.
        Returns the fixed config.
        """

        if len(self.logs_cache) == 0:
            print("no deployments attempted. Returning og stack.")
            return self.config

        prompt = f"""
            Terraform config:
            {self.config.template}

            Deployment logs:
            {'Log Message:'.join(map(str, self.logs_cache))}
        """

        if (
            diagnosed_issue == DiagnoserState.DEPLOYABLE
        ):  # No action. config is good as is.
            return self.config
        elif (
            diagnosed_issue == DiagnoserState.MISSING_OR_INVALID_DATA
            or diagnosed_issue == DiagnoserState.OTHER
        ):
            # Need to basically verify that the tf config's info that is broken can be
            # fixed/is a stupid mistake rather than user issue.
            response = prompt_with_file(
                BASE_PROMPT_PATH + VERIFY_CONSTRUCTED_CONFIG,
                prompt,
                self.llm_client,
                is_json=False,
            )

            if len(response) == 0:
                print("Stack reqires some info from user. Returning custom msg.")
                raise TFConfigRequiresUserInfoException

            print(f"Fixed tf config: {response}")
            return TerraformConfig(response, self.config.name)

        raise DeploymentBrokenException

    def determine_config_deployability(
        self, current_state: ChatSessionState
    ) -> DiagnoserState:
        """
        A binary classifier that returns whether the config can be deployed or not.
        """
        # If the config has been deployed before, check logs to see for failures. If there are logs, return missing state.
        if (
            current_state == ChatSessionState.DEPLOYMENT_FAILED
            and len(self.logs_cache) > 0
        ):
            return DiagnoserState.MISSING_OR_INVALID_DATA
        elif (
            current_state == ChatSessionState.DEPLOYMENT_SUCCEEDED
            or current_state == ChatSessionState.QUERIED_AND_DEPLOYABLE
        ):
            return DiagnoserState.DEPLOYABLE

        return DiagnoserState.OTHER


class DeployTFConfigAction(base.AbstractAction):
    """
    An action to deploy a cf stack to a user's account
    """

    def __init__(
        self,
        user_config: TerraformConfig,
        chat_session_id: UUID,
        state_manager: SupaClient,
        # user_aws_secret_key: str,
        # user_aws_access_key_id: str,
        tf_file_dir: str,
    ) -> None:
        """
        Constructs a user deployment action
        """
        super().__init__()
        # self.user_secret_key = user_aws_secret_key
        # self.user_aws_access_key_id = user_aws_access_key_id

        # self.cf_client = boto3.client(
        #     "cloudformation",
        #     aws_access_key_id=self.user_aws_access_key_id,
        #     aws_secret_access_key=self.user_secret_key,
        # )

        self.user_config = user_config
        self.state_manager = state_manager
        self.chat_session_id = chat_session_id
        self.diagnoser = Diagnoser(self.user_config, self.claude_client)

        self.tf_client = Terraform(working_dir=tf_file_dir)
        self.tf_client.init()
        self.tf_file_dir = tf_file_dir

    def request_deployment_info(self) -> str:
        """
        Coalesce a response to the user requesting the remaining info for a deployment.
        Consider's the user's input as well.
        """

        prompt = f"""
            terraform config:
            {self.user_config.template}
            
            logs:
            {json.dumps(', '.join(list(self.diagnoser.logs_cache)))}
        """

        # TODO also use self.diagnoser.logs_cache to check exactly what is needed.
        # TODO also check outputs if any and include as context
        response = prompt_with_file(
            BASE_PROMPT_PATH + REQUEST_DEPLOYMENT_INFO_PROMPT, prompt, self.gpt_client
        )

        self.state_manager.update_chat_session_state(
            self.chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
        )

        return response

    def destroy(self) -> str:
        """
        Destroys the failed config deployed by self.tf_client
        """
        print("Destroying the failed configuration...")
        return_code, _, destroy_stderr = self.tf_client.cmd("destroy", "-auto-approve")
        if return_code != 0:
            self.diagnoser.logs_cache.append(destroy_stderr)
            return destroy_stderr

        return DESTROY_SUCCESS

    def deploy_config(self) -> Tuple[str, ChatSessionState]:
        """
        Deploys user's tf config into their account
        """

        state: ChatSessionState
        response = None

        try:
            # 1. TODO if the template doesn't exist at the dir path, load it in with the supa client

            # Marking the deployment as in progress
            state = ChatSessionState.DEPLOYMENT_IN_PROGRESS
            self.state_manager.update_chat_session_state(
                self.chat_session_id, ChatSessionState.DEPLOYMENT_IN_PROGRESS
            )

            # Apply the changes and capture the output
            return_code, _, apply_stderr = self.tf_client.apply(
                skip_plan=True, capture_output=True, raise_on_error=False
            )

            if return_code != 0:
                print("Terraform apply failed.")
                print(apply_stderr)
                self.diagnoser.logs_cache.append(apply_stderr)
                raise DeploymentBrokenException

            print(f"Config {self.user_config.name} deployment complete.")
            state = ChatSessionState.DEPLOYMENT_SUCCEEDED
            response = SUCCESS_RESPONSE
        except Exception as e:
            print(f"Error during stack deployment: {e}")
            state = ChatSessionState.DEPLOYMENT_FAILED
            response = ERROR_RESPONSE
        finally:
            self.state_manager.update_chat_session_state(self.chat_session_id, state)

        if state == ChatSessionState.DEPLOYMENT_FAILED:
            self.destroy()
            response = ERROR_RESPONSE

        return str(response), state

    def handle_failed_deployment(self, diagnosed_issue: DiagnoserState) -> str:
        """
        Handles a failed deployment with the Diagnoser class.
        Returns a message to the user
        """

        def return_user_request() -> str:
            """
            A small helper that requests deployment info from the user.
            """
            print("Deployment requires user info. Returning specific request message.")
            ret_msg = self.request_deployment_info()
            self.diagnoser.logs_cache.clear()
            return ret_msg

        try:
            new_stack = self.diagnoser.fix_broken_config(diagnosed_issue)
            for i in range(NUM_RETRIES):
                self.diagnoser.logs_cache.clear()
                _, state = self.deploy_config()
                print(f"state after {i} deployment: {state}")

                if state == ChatSessionState.DEPLOYMENT_SUCCEEDED:
                    self.user_config = new_stack
                    return SUCCESS_RESPONSE

                deployability = self.diagnoser.determine_config_deployability(state)
                print(deployability)
                print(f"logs length: {len(self.diagnoser.logs_cache)}")
                new_stack = self.diagnoser.fix_broken_config(deployability)

            ret_msg = return_user_request()
        except TFConfigRequiresUserInfoException:
            ret_msg = return_user_request()
        except Exception as e:
            # At this point, we're cooked. So going to relinquish the log cache.
            print(f"Error handling failed deployment: {e}")
            ret_msg = return_user_request()
            self.diagnoser.logs_cache.clear()

        print("Couldn't diagnose error properly. Returning complete failure response.")
        return ret_msg

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
        elif (
            state == ChatSessionState.QUERIED_AND_DEPLOYABLE
        ):  # 1.e If deployable but not deployed, run deployment.
            response, state = self.deploy_config()
        elif (
            state == ChatSessionState.QUERIED
            or state == ChatSessionState.QUERIED_NOT_DEPLOYABLE
        ):
            # 2. if never deployed, validate stack is deployable
            diagnoser_decision = self.diagnoser.determine_config_deployability(state)

            #   2.a if not deployable, call diagnoser with same retry/missing info requests
            if diagnoser_decision != DiagnoserState.MISSING_OR_INVALID_DATA:
                response, state = (
                    self.deploy_config()
                )  # 2.b if deployable, attempt deployment.
                if state == ChatSessionState.DEPLOYMENT_SUCCEEDED:
                    # 2.b.1 if succeeded, return msg saying deployment succeeded
                    return SUCCESS_RESPONSE

            return self.handle_failed_deployment(
                diagnoser_decision
            )  # 2.b.2 if failed, call diagnoser with same retry/missing info requests

        elif state == ChatSessionState.NOT_QUERIED:
            # return msg saying you haven't given me any specs. what am i supposed to do lol.
            response = NO_INPUT_YET_RESPONSE
        elif state == ChatSessionState.DEPLOYMENT_FAILED:
            # return some kind of error message to the user
            pass

        if state == ChatSessionState.DEPLOYMENT_FAILED:
            diagnoser_decision = self.diagnoser.determine_config_deployability(state)
            print(f"Diagnosed decision in beginning: {diagnoser_decision}")
            response = self.handle_failed_deployment(diagnoser_decision)

        return response
