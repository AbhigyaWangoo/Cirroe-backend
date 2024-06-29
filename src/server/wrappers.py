from src.model.stack import CloudFormationStack
from src.actions.construct import ConstructCFStackAction
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
        print(stack)
        print(action_response)

        client = SupaClient(user_id)
        response = client.upload_cf_stack(stack)

        chat_session_id=response.data[0][ID]
        # TODO add cloudformation stack linter to see if
        # the stack is deployable, and update the state as such
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED)

        return action_response
    except Exception as e:
        print(
            f"Failed to construct cf stack for user {user_id}. \nUser request: {user_query} \n\nError: {e}"
        )
        client.update_chat_session_state(chat_session_id, ChatSessionState.QUERIED_NOT_DEPLOYABLE)

def query_wrapper(user_query: str, user_id: int, is_construction: bool):
    """
    A wrapper around a Cirrus query. 
    """
    # This fn will do the following:
    # 1. rcv a query from the user, the user's id, and a bool indicating whether this is a new chatsession or not
    # 2. If new chat sesh, call construct action
    # 3. if existing, call edit
    # 4. if user requests a deployment, call deploy action