from src.actions.construct import ConstructTFConfigAction
from src.actions.edit import EditTFConfigAction
import shutil
from src.actions.deploy import DeployTFConfigAction, ERROR_RESPONSE
from src.db.supa import SupaClient, ChatSessionState, TFConfigDNEException
from src.model.stack import TerraformConfig
import os
from collections import deque

from include.utils import BASE_PROMPT_PATH, prompt_with_file
from include.llm.gpt import GPTClient

CONSTRUCT_OR_OTHER_PROMPT = "construct_or_other.txt"
EDIT_OR_OTHER_PROMPT = "edit_or_other.txt"
IRRELEVANT_QUERY_HANDLER = "handle_irrelevant_query.txt"

CHAT_CACHE_LIMIT = 5
chat_cache = deque(maxlen=CHAT_CACHE_LIMIT)


def construction_wrapper(
    user_query: str, chat_session_id: int, client: SupaClient
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
    user_query: str, chat_session_id: str, client: SupaClient, config: TerraformConfig
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


def setup_deployment_action(user_id: int, chat_session_id: int) -> DeployTFConfigAction:
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


def destroy_wrapper(user_id: int, chat_session_id: int):
    """
    Wrapper around a destruction action. Allows us to destroy
    a setup from the user's request.
    """
    action = setup_deployment_action(user_id, chat_session_id)

    dir_path = os.path.join("include/data/", str(chat_session_id))
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

    return action.destroy()


def deploy_wrapper(user_id: int, chat_session_id: int) -> str:
    """
    A wrapper around the deployment action. Allows us to deploy a
    cf stack from the user.
    """
    deployment_action = setup_deployment_action(user_id, chat_session_id)

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
    print(response)

    return response


def get_memory(user_query: str) -> str:
    """
    Returns a perfect string of the memory
    from the last few chats from the user so
    far. Takes the user query to append to the
    end.
    """

    if len(chat_cache) == 0:
        return user_query

    mem = """
        Here are a set of previous chats between you and the user. Use them to 
        inform your response to the user.
    """

    for chat in chat_cache:
        mem += chat

    final_chunk = f"""
        Now, here is the new query from the user.
        {user_query}
    """

    return mem + final_chunk


def query_wrapper(user_query: str, user_id: int, chat_session_id: int) -> str:
    """
    A wrapper around a Cirroe query. Determines whether the input query is a
    construction call, or an edit call. For now, we're not allowing deployments from chat.
    """

    # 1. Get state.
    supa_client = SupaClient(user_id)
    client = GPTClient()
    config = None

    memory_powered_query = get_memory(user_query)
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
            # The config absoloutly should exist here.
            # user_query: str, chat_session_id: str, client: SupaClient, config: TerraformConfig
            response = edit_wrapper(memory_powered_query, chat_session_id, supa_client, config)
        else:
            response = handle_irrelevant_query(memory_powered_query, client)

    back_and_forth_str = f"""
        q: {user_query}
        a: {response}
    """
    chat_cache.append(back_and_forth_str)

    return response
