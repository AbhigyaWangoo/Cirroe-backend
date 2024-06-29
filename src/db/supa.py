from src.model.stack import CloudFormationStack
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.client import ClientOptions
from enum import Enum, StrEnum

# DB Column names
CF_STACK_COL_NAME = "CirrusTemplate"
ID = "id"


class Operation(Enum):
    CREATE = 0
    READ = 1
    UPDATE = 2
    DELETE = 3


class Table(StrEnum):
    USERS = "Users"
    CHAT_SESSIONS = "ChatSessions"
    CHATS = "Chats"


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
            .insert({"UserId": self.user_id, CF_STACK_COL_NAME: stack.template})
            .execute()
        )

        return response

    def get_cf_stack(self, chat_session_id: int) -> CloudFormationStack:
        """
        Given the chat session id, get the cf stack.
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .select(CF_STACK_COL_NAME)
            .eq("id", chat_session_id)
            .execute()
        ).data[0]

        return CloudFormationStack(response[CF_STACK_COL_NAME], "")

    def edit_entire_cf_stack(
        self, chat_session_id: int, new_stack: CloudFormationStack
    ):
        """
        Alter an existing cf stack with the new one.
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .update({CF_STACK_COL_NAME: new_stack.template})
            .eq("id", chat_session_id)
            .execute()
        )

        return response
