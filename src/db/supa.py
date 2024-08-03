from src.model.stack import TerraformConfig
from include.utils import hash_str
from typeguard import typechecked
from uuid import UUID
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.client import ClientOptions
from enum import Enum, StrEnum

from typing import Tuple, List, Dict

# DB Column names
TF_CONFIG_COL_NAME = "config"
STATE_COL_NAME = "state"
STACK_NAME_COL = "config_name"
ID = "id"

USER_MSG = "user_msg"
SYSTEM_MSG = "system_msg"
CHAT_SESSION_ID = "chat_session_id"

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
    USERS = "UserBindings"
    CHAT_SESSIONS = "ChatSessions"
    CHATS = "Chats"


class TFConfigDNEException(Exception):
    """
    Represents cases where a stack doesn't exist in db yet
    """

    pass

@typechecked
class SupaClient:
    """
    Supabase db client
    """

    def __init__(self, user_id: UUID) -> None:
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

    def upload_cf_stack(self, stack: TerraformConfig):
        """
        Uploads a CF stack template to the correct chatsession
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .insert(
                {
                    "UserId": self.user_id,
                    TF_CONFIG_COL_NAME: stack.template,
                    STACK_NAME_COL: stack.name,
                }
            )
            .execute()
        )

        return response

    def get_tf_config(self, chat_session_id: UUID) -> TerraformConfig:
        """
        Given the chat session id, get the tf config.
        """

        val = chat_session_id
        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .select(STACK_NAME_COL, TF_CONFIG_COL_NAME)
            .eq(ID, str(val))
            .execute()
        ).data

        if len(response) == 0:
            raise TFConfigDNEException

        response = response[0]
        if response[TF_CONFIG_COL_NAME] is None:
            raise TFConfigDNEException

        if response[STACK_NAME_COL] is None:
            new_name = hash_str(chat_session_id)
            print(
                f"Name of stack with id {chat_session_id} was none. setting it to {new_name}"
            )
            response[STACK_NAME_COL] = new_name
            self.edit_entire_tf_config(
                chat_session_id,
                TerraformConfig(response[TF_CONFIG_COL_NAME], response[STACK_NAME_COL]),
            )

        return TerraformConfig(response[TF_CONFIG_COL_NAME], response[STACK_NAME_COL])

    @typechecked
    def edit_entire_tf_config(self, chat_session_id: UUID, new_config: TerraformConfig):
        """
        Alter an existing cf stack with the new one.
        """

        response = (
            self.supabase.table(Table.CHAT_SESSIONS)
            .update(
                {
                    TF_CONFIG_COL_NAME: new_config.template,
                    STACK_NAME_COL: new_config.name,
                }
            )
            .eq(ID, chat_session_id)
            .execute()
        )

        return response

    def update_chat_session_state(
        self, chat_session_id: UUID, new_state: ChatSessionState
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

    def get_chat_session_state(self, chat_session_id: UUID) -> ChatSessionState:
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

    def get_user_aws_creds(self) -> Tuple[str, str]:
        """
        Returns the user's aws credentials in the following format:
        aws_secret_key, aws_access_key_id

        TODO as of now this just returns mine. Need to alter to provide
        user supplied aws creds.
        """
        secret = os.environ.get("DEMO_AWS_SECRET_ACCESS_KEY", "")
        access = os.environ.get("DEMO_AWS_ACCESS_KEY_ID", "")
        return secret, access

    def add_chat(self, chat_session_id: UUID, user_msg: str, system_msg: str):
        """
        Adds a 'back and forth' message between the user and the system
        """

        response = (
            self.supabase.table(Table.CHATS)
            .insert(
                {
                    CHAT_SESSION_ID: str(chat_session_id),
                    USER_MSG: user_msg,
                    SYSTEM_MSG: system_msg
                }
            )
            .execute()
        )

        return response

    def get_chats(self, chat_session_id: UUID) -> List[Dict[str, str]]:
        """
        Returns chats in this format:
        
        [
            {
                system: <system chat>,
                user: <user chat>
            }
        ]
        """

        response = (
            self.supabase.table(Table.CHATS)
            .select(USER_MSG, SYSTEM_MSG)
            .eq(CHAT_SESSION_ID, chat_session_id)
            .execute()
        )

        return response.data
