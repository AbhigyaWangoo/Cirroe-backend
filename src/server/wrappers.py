from src.actions.construct import ConstructCFStackAction
from src.actions.edit import EditCFStackAction
from src.db.supa import SupaClient, ChatSessionState, ID


def construction_wrapper(user_id: int, user_query: str) -> str:
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

        client = SupaClient(user_id)
        response = client.upload_cf_stack(stack)

        chat_session_id = response.data[0][ID]
        # TODO add cloudformation stack linter to see if
        # the stack is deployable, and update the state as such
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED)

        return action_response
    except Exception as e:
        print(
            f"Failed to construct cf stack for user {user_id}. \nUser request: {user_query} \n\nError: {e}"
        )
        client.update_chat_session_state(
            chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
        )


def edit_wrapper(user_query: str, user_id: int, chat_session_id: str):
    """
    Using the user query, and the cf stack retrieved from supabase with the chat
    session id, edits the cf stack and responds qualitativly to the user.

    also, updates state and persists chat stack.
    """

    try:
        # 1. retrieve stack with chat session id
        client = SupaClient(user_id)
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
    except Exception as e:
        print(
            f"Failed to edit cf stack for user {user_id}. \nUser request: {user_query} \n\nError: {e}"
        )
        client.update_chat_session_state(
            chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE
        )


def query_wrapper(user_query: str, user_id: int, is_construction: bool):
    """
    A wrapper around a Cirrus query.
    """
    # This fn will do the following:
    # 1. rcv a query from the user, the user's id, and a bool indicating whether this is a new chatsession or not
    # 2. If new chat sesh, call construct action
    # 3. if existing, call edit
    # 4. if user requests a deployment, call deploy action
