from src.actions.construct import ConstructTFConfigAction
from src.actions.execute import ExecutionAction
from uuid import UUID
from src.actions.edit import EditTFConfigAction
import shutil
from src.actions.deploy import DeployTFConfigAction, ERROR_RESPONSE
from src.db.supa import SupaClient, ChatSessionState, TFConfigDNEException, CredentialsNotProvidedException
from src.model.stack import TerraformConfig
import os

from include.utils import BASE_PROMPT_PATH, prompt_with_file
from include.llm.gpt import GPTClient

CONSTRUCT_OR_OTHER_PROMPT = "construct_or_other.txt"
EDIT_OR_OTHER_PROMPT = "edit_or_other.txt"
IRRELEVANT_QUERY_HANDLER = "handle_irrelevant_query.txt"

FILL_UP_MORE_CREDITS = "Refill credits to continue."
CREDENTIALS_NOT_PROVIDED = "Looks like you're missing some auth credentials. Please fill them in properly, or contact support for more info."

# AWS_CREDENTIALS_FILE="~/.aws/credentials"
AWS_CREDENTIALS_FILE = os.path.expanduser('~/.aws/credentials')

def construction_wrapper(
    user_query: str, chat_session_id: UUID, client: SupaClient
) -> str:
    """
    Constructs a terraform config based off user query. Persists config in supabase and updates
    chat session state. Returns qualitative response for user.

    todo Caches ChatSession config in mem and disk for further use.
    Caches user supa client connection in mem.
    """
    action = ConstructTFConfigAction()

    try:
        action_response = action.trigger_action(user_query)
        stack = action.tf_config

        client.edit_entire_tf_config(chat_session_id, stack)

        # TODO add cloudformation stack linter to see if
        # the stack is deployable, and update the state as such
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED)

        return action_response
    except Exception as e:
        print(
            f"Failed to construct tf config for user. \nUser request: {user_query} \n\nError: {e}"
        )
        client.update_chat_session_state(
            chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
        )


def edit_wrapper(
    user_query: str, chat_session_id: UUID, client: SupaClient, config: TerraformConfig
) -> str | None:
    """
    Using the user query, and the cf stack retrieved from supabase with the chat
    session id, edits the cf stack and responds qualitativly to the user.

    also, updates state and persists chat stack.
    """

    try:
        # 2. construct edit action
        action = EditTFConfigAction(config)

        # 3. trigger action
        action_result = action.trigger_action(user_query)
        new_config = action.new_config
        print(new_config)

        # 4. persist new stack in supa
        client.edit_entire_tf_config(chat_session_id, new_config)
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED)

        return action_result
    except TFConfigDNEException:
        print("Stack dne yet. Edit wrapper incorrect.")
        return None
    except Exception as e:
        print(
            f"Failed to edit cf stack for user. \nUser request: {user_query} \n\nError: {e}"
        )
        client.update_chat_session_state(
            chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
        )
        return None


def setup_deployment_action(user_id: UUID, chat_session_id: UUID) -> DeployTFConfigAction:
    """
    Sets up and returns a deployment action for usage.
    """
    supa_client = SupaClient(user_id)
    user_config = supa_client.get_tf_config(chat_session_id)

    dir_path = os.path.join("include/data/", str(chat_session_id))

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    file_path = os.path.join(dir_path, user_config.name)

    if os.path.exists(file_path):
        # We've aready tried this before. Construct the user config from that provided value
        pass

    with open(f"{file_path}.tf", "w", encoding="utf8") as file:
        file.write(user_config.template)

    deployment_action = DeployTFConfigAction(
        user_config, chat_session_id, supa_client, dir_path
    )

    return deployment_action


def destroy_wrapper(user_id: UUID, chat_session_id: UUID):
    """
    Wrapper around a destruction action. Allows us to destroy
    a setup from the user's request.
    """
    try:
        action = setup_deployment_action(user_id, chat_session_id)
    except CredentialsNotProvidedException:
        return CREDENTIALS_NOT_PROVIDED

    response = action.destroy()

    SupaClient(user_id).update_chat_session_state(chat_session_id, ChatSessionState.QUERIED_AND_DEPLOYABLE)

    dir_path = os.path.join("include/data/", str(chat_session_id))
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

    return response


def deploy_wrapper(user_id: UUID, chat_session_id: UUID) -> str:
    """
    A wrapper around the deployment action. Allows us to deploy a
    cf stack from the user.
    """
    try:
        deployment_action = setup_deployment_action(user_id, chat_session_id)
    except CredentialsNotProvidedException:
        return CREDENTIALS_NOT_PROVIDED

    # 2. Attempt deployment, return trigger_action response
    response = deployment_action.trigger_action()

    dir_path = os.path.join("include/data/", str(chat_session_id))
    if response == ERROR_RESPONSE:
        shutil.rmtree(dir_path)  # TODO fix this inna bit

    return response


def handle_irrelevant_query(query: str, client: GPTClient) -> str:
    """
    Hanldes and responds to a query that isn't clearly about creating or
    deploying infra. If the query is asking some questions about aws, or how
    this thing works, then answer, else respond with a msg saying pls be specific.
    """
    response = prompt_with_file(
        BASE_PROMPT_PATH + IRRELEVANT_QUERY_HANDLER,
        query,
        client,
    )

    return response

def point_execution_wrapper(user_query: str, user_id: UUID, supa_client: SupaClient) -> str:
    """
    A wrapper around point executions. Check the ExecutionAction class for more info.
    """

    secret, access, region = supa_client.get_user_aws_preferences()

    with open(AWS_CREDENTIALS_FILE, "r", encoding="utf8") as fp:
        creds = fp.read()
        if str(user_id) not in creds:
            with open(AWS_CREDENTIALS_FILE, "a", encoding="utf8") as fpw:
                new_profile = f"\n[{str(user_id)}]\naws_access_key_id = {access}\naws_secret_access_key = {secret}\nregion = {region}"

                fpw.write(new_profile)

        action = ExecutionAction(str(user_id))

        return action.trigger_action(user_query)

def query_wrapper(user_query: str, user_id: UUID, chat_session_id: UUID) -> str:
    """
    A wrapper around a Cirroe query. Determines whether the input query is a
    construction call, or an edit call. For now, we're not allowing deployments from chat.
    """

    # 1. Get state.
    supa_client = SupaClient(user_id)
    client = GPTClient()
    config = None

    can_query = supa_client.user_can_query()
    if not can_query:
        return FILL_UP_MORE_CREDITS

    memory_powered_query = supa_client.get_memory_str(chat_session_id, user_query)

    state = supa_client.get_chat_session_state(chat_session_id)
    if state == ChatSessionState.DEPLOYMENT_SUCCEEDED or state == ChatSessionState.DEPLOYMENT_IN_PROGRESS:
        return point_execution_wrapper(memory_powered_query, user_id, supa_client)

    try:
        config = supa_client.get_tf_config(chat_session_id)
        need_to_construct = False
    except TFConfigDNEException:
        # determine the type of query
        response = prompt_with_file(
            BASE_PROMPT_PATH + CONSTRUCT_OR_OTHER_PROMPT, memory_powered_query, client
        )
        need_to_construct = response.lower() == "true"

    if need_to_construct:
        # if never been queried before, only then can this be a construction action
        response = construction_wrapper(user_query, chat_session_id, supa_client)
    else:
        response = prompt_with_file(
            BASE_PROMPT_PATH + EDIT_OR_OTHER_PROMPT, memory_powered_query, client
        )
        need_to_edit = response.lower() == "true"

        if need_to_edit:
            # The config def should exist here.
            response = edit_wrapper(memory_powered_query, chat_session_id, supa_client, config)
        else:
            response = handle_irrelevant_query(memory_powered_query, client)

    supa_client.add_chat(chat_session_id, user_query, response)

    return response
