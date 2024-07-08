from src.actions.construct import ConstructCFStackAction
from src.actions.edit import EditCFStackAction
from src.db.supa import SupaClient, ChatSessionState, StackDNEException
from src.model.stack import CloudFormationStack

from include.utils import BASE_PROMPT_PATH, prompt_with_file
from include.llm.gpt import GPTClient

CONSTRUCT_OR_OTHER_PROMPT = "construct_or_other.txt"
IRRELEVANT_QUERY_HANDLER = "handle_irrelevant_query.txt"


def construction_wrapper(
    user_query: str, chat_session_id: int, client: SupaClient
) -> str:
    """
    Constructs a stack based off user query. Persists stack in supabase and updates
    chat session state. Returns qualitative response for user.

    todo Caches ChatSession stack in mem and disk for further use.
    Caches user supa client connection in mem.
    """
    action = ConstructCFStackAction()

    try:
        action_response = action.trigger_action(user_query)
        stack = action.stack

        client.edit_entire_cf_stack(chat_session_id, stack)

        # TODO add cloudformation stack linter to see if
        # the stack is deployable, and update the state as such
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED)

        return action_response
    except Exception as e:
        print(
            f"Failed to construct cf stack for user. \nUser request: {user_query} \n\nError: {e}"
        )
        client.update_chat_session_state(
            chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
        )


def edit_wrapper(
    user_query: str, chat_session_id: str, client: SupaClient
) -> str | None:
    """
    Using the user query, and the cf stack retrieved from supabase with the chat
    session id, edits the cf stack and responds qualitativly to the user.

    also, updates state and persists chat stack.
    """

    try:
        # 1. retrieve stack with chat session id
        stack = client.get_cf_stack(chat_session_id)

        # 2. construct edit action
        action = EditCFStackAction(stack)

        # 3. trigger action
        action_result = action.trigger_action(user_query)
        new_stack = action.new_stack
        print(new_stack)

        # 4. persist new stack in supa
        client.edit_entire_cf_stack(chat_session_id, new_stack)
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED)

        return action_result
    except StackDNEException:
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


def deploy_wrapper(user_id: int, chat_session_id: int) -> str:
    pass


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


def query_wrapper(user_query: str, user_id: int, chat_session_id: int) -> str:
    """
    A wrapper around a Cirrus query. Determines whether the input query is a
    construction call, or an edit call. For now, we're not allowing deployments from chat.
    """

    # 1. Get state.
    supa_client = SupaClient(user_id)
    client = GPTClient()
    stack: CloudFormationStack | None = None

    state = supa_client.get_chat_session_state(chat_session_id)
    if state == ChatSessionState.NOT_QUERIED:
        # 2. if never been queried before, only then can this be a construction action
        response = prompt_with_file(
            BASE_PROMPT_PATH + CONSTRUCT_OR_OTHER_PROMPT, user_query, client
        )

        if response.lower() == "true":
            response = construction_wrapper(user_query, chat_session_id, supa_client)
        else:
            response = handle_irrelevant_query(user_query, client)
    else:
        # 3. if exists, can only be edit. assumes that edit action will
        # handle even if no edits are possible.
        if stack:
            response = edit_wrapper(user_query, chat_session_id, supa_client)

            if response is None:
                response = handle_irrelevant_query(user_query, client)

    return response
