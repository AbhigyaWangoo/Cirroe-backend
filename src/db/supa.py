from src.model.stack import CloudFormationStack
from include.utils import hash_str
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.client import ClientOptions
from enum import Enum, StrEnum

# DB Column names
CF_STACK_COL_NAME = "CirrusTemplate"
STATE_COL_NAME = "State"
STACK_NAME_COL = "StackName"
ID = "id"


class Operation(Enum):
    CREATE = 0
    READ = 1
    UPDATE = 2
    DELETE = 3


class ChatSessionState(Enum):
    NOT_QUERIED = 0
    QUERIED_NOT_DEPLOYABLE = 1
    QUERIED_AND_DEPLOYABLE = 2
    DEPLOYMENT_FAILED = 3
    DEPLOYMENT_IN_PROGRESS = 4
    DEPLOYMENT_SUCCEEDED = 5
    QUERIED = 6


class Table(StrEnum):
    USERS = "Users"
    CHAT_SESSIONS = "ChatSessions"
    CHATS = "Chats"


class StackDNEException(Exception):
    """
    Represents cases where a stack doesn't exist in db yet
    """

    pass


class SupaClient:
    """
    Supabase db client
    """

    def __init__(self, user_id: int) -> None:
        load_dotenv()

        self.user_id = user_id
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_API_KEY")
        self.supabase: Client = None

        try:
            self.supabase = create_client(
                url,
                key,
                options=ClientOptions(
                    postgrest_client_timeout=10,
                    storage_client_timeout=10,
                    schema="public",
                ),
            )
        except Exception as e:
            raise ConnectionError(f"Error: Couldn't connect to supabase db. {e}")

    def upload_cf_stack(self, stack: CloudFormationStack):
        """
        Uploads a CF stack template to the correct chatsession
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .insert(
                {
                    "UserId": self.user_id,
                    CF_STACK_COL_NAME: stack.template,
                    STACK_NAME_COL: stack.name,
                }
            )
            .execute()
        )

        return response

    def get_cf_stack(self, chat_session_id: int) -> CloudFormationStack:
        """
        Given the chat session id, get the cf stack.
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .select(STACK_NAME_COL, CF_STACK_COL_NAME)
            .eq(ID, chat_session_id)
            .execute()
        ).data[0]

        if response[CF_STACK_COL_NAME] is None:
            raise StackDNEException

        if response[STACK_NAME_COL] is None:
            new_name = hash_str(str(chat_session_id))
            print(
                f"Name of stack with id {chat_session_id} was none. setting it to {new_name}"
            )
            response[STACK_NAME_COL] = new_name
            self.edit_entire_cf_stack(
                chat_session_id,
                CloudFormationStack(
                    response[CF_STACK_COL_NAME], response[STACK_NAME_COL]
                ),
            )

        return CloudFormationStack(
            response[CF_STACK_COL_NAME], response[STACK_NAME_COL]
        )

    def edit_entire_cf_stack(
        self, chat_session_id: int, new_stack: CloudFormationStack
    ):
        """
        Alter an existing cf stack with the new one.
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .update(
                {CF_STACK_COL_NAME: new_stack.template, STACK_NAME_COL: new_stack.name}
            )
            .eq(ID, chat_session_id)
            .execute()
        )

        return response

    def update_chat_session_state(
        self, chat_session_id: int, new_state: ChatSessionState
    ):
        """
        Alter the state of a chat session
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .update({STATE_COL_NAME: new_state.name})
            .eq(ID, chat_session_id)
            .execute()
        )

        return response

    def get_chat_session_state(self, chat_session_id: int) -> ChatSessionState:
        """
        Get the state of a chat session
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .select(STATE_COL_NAME)
            .eq(ID, chat_session_id)
            .execute()
        )

        return ChatSessionState[response.data[0][STATE_COL_NAME]]
