import subprocess
from src.actions.execute import ExecutionAction
from uuid import UUID
from src.db.supa import (
    SupaClient,
    ChatSessionState,
    CredentialsNotProvidedException,
)
import os

from include.utils import BASE_PROMPT_PATH
from include.llm.claude import ClaudeClient
from include.llm.base import AbstractLLMClient

from dotenv import load_dotenv

load_dotenv()

CONSTRUCT_OR_OTHER_PROMPT = "construct_or_other.txt"
EDIT_OR_OTHER_PROMPT = "edit_or_other.txt"
IRRELEVANT_QUERY_HANDLER = "handle_irrelevant_query.txt"

FILL_UP_MORE_CREDITS = "Refill credits to continue."
CREDENTIALS_NOT_PROVIDED = 'Looks like you\'re missing some auth credentials. Please fill them in properly, or contact support for more info. Just navigate to the hamburger menu above, click "Set AWS Credentials", and fill in your AWS secret and access keys.'
NOTHING_TO_DEPLOY = "User config dne. Setup deployment action shouldn't work here."

AWS_SHARED_CREDENTIALS_FILE = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")

def handle_irrelevant_query(query: str, client: AbstractLLMClient) -> str:
    """
    Hanldes and responds to a query that isn't clearly about creating or
    deploying infra. If the query is asking some questions about aws, or how
    this thing works, then answer, else respond with a msg saying pls be specific.
    """

    with open(BASE_PROMPT_PATH + IRRELEVANT_QUERY_HANDLER, "r", encoding="utf8") as fp:
        prompt = fp.read()
        new_prompt = prompt.format(query)

        return client.query(new_prompt, "", is_json=False, temperature=0.5)


def point_execution_wrapper(
    user_query: str, user_id: UUID, supa_client: SupaClient
) -> str:
    """
    A wrapper around point executions. Check the ExecutionAction class for more info.
    """

    secret, access, region = supa_client.get_user_aws_preferences()

    def append_creds_to_file(
        aws_file: str, secret: str, access: str, region: str, mode: str = "a"
    ):
        with open(aws_file, mode, encoding="utf8") as fpw:
            if mode == "a":
                fpw.write("\n")

            new_profile = f"[{str(user_id)}]\naws_access_key_id = {access}\naws_secret_access_key = {secret}\nregion = {region}"
            fpw.write(new_profile)

    if os.path.exists(AWS_SHARED_CREDENTIALS_FILE):
        with open(AWS_SHARED_CREDENTIALS_FILE, "r", encoding="utf8") as fp:
            creds = fp.read()
            if str(user_id) not in creds:
                append_creds_to_file(
                    AWS_SHARED_CREDENTIALS_FILE, secret, access, region
                )
    else:
        append_creds_to_file(AWS_SHARED_CREDENTIALS_FILE, secret, access, region, "w")

    action = ExecutionAction(str(user_id))

    return action.trigger_action(user_query)


def query_wrapper(user_query: str, user_id: UUID, chat_session_id: UUID) -> str:
    """
    A wrapper around a Cirroe query. Determines whether the input query is a
    construction call, or an edit call. For now, we're not allowing deployments from chat.
    """

    try:
        # 1. Get state.
        supa_client = SupaClient(user_id)
        # client = GPTClient()
        llm_client = ClaudeClient()

        can_query = supa_client.user_can_query()
        if not can_query:
            return FILL_UP_MORE_CREDITS

        memory_powered_query = supa_client.get_memory_str(chat_session_id, user_query)

        state = supa_client.get_chat_session_state(chat_session_id)
        execution_action = ExecutionAction(str(user_id))
        response=""
        if (
            state == ChatSessionState.DEPLOYMENT_SUCCEEDED
            or state == ChatSessionState.DEPLOYMENT_IN_PROGRESS
            or execution_action.is_point_execution(memory_powered_query)
        ):
                response = point_execution_wrapper(
                    memory_powered_query, user_id, supa_client
                )

        response = handle_irrelevant_query(memory_powered_query, llm_client)

    except subprocess.CalledProcessError:
        # TODO Add metric
        print("Point execution failed")
    except CredentialsNotProvidedException:
        return CREDENTIALS_NOT_PROVIDED
    except Exception as e:
        print("Something else went wrong: " + e)
    else:
        supa_client.add_chat(chat_session_id, user_query, response)

    return response
