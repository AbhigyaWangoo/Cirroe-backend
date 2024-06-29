from src.model.stack import CloudFormationStack
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.client import ClientOptions
from enum import Enum

# DB Column names
CF_STACK_COL_NAME="CirrusTemplate"

class Operation(Enum):
    CREATE=0
    READ=1
    UPDATE=2
    DELETE=3
        
class Table(Enum):
    USERS=0
    CHAT_SESSIONS=1
    CHATS=2

class SupaClient:
    """
    Supabase db client
    """
    def __init__(self, user_id: int) -> None:
        load_dotenv()
        
        
        self.user_id=user_id
        url: str = os.environ.get("SUPABASE_URI")
        key: str = os.environ.get("SUPABASE_API_KEY")
        self.supabase: Client = None

        try:
            self.supabase = create_client(url, key,
            options=ClientOptions(
                postgrest_client_timeout=10,
                storage_client_timeout=10,
                schema="public",
            ))
        except Exception as e:
            raise ConnectionError(f"Error: Couldn't connect to supabase db. {e}")

    def perform_column_action(self, table: Table, action: Operation, *columns, **edit_columns):
        """
        Given a table and an operation, performs the desired operation. 

        For deletes, you need to only have 2 column values. The column that you want to delete 
        from, and the desired value.
        
        For updates, your edit columns need to have all the key value pairs of new column <-> value 
        pairs and your columns need to be 2 values, representing the <column> == <value> on the row 
        to update
        """

        if action == Operation.READ:
            if edit_columns: # indicates we have multiple columns to read by
                keys = list(edit_columns.keys())
                values = list(edit_columns.values())

                return (
                    self.supabase.table(table)
                    .select(*keys)
                    .eq(*values)
                    .execute()
                )["data"]

            return self.supabase.table(table).select(f"{','.join(columns)}").execute()["data"]
        elif action == Operation.CREATE:
            return self.supabase.table(table).insert(edit_columns).execute()["data"]
        elif action == Operation.UPDATE:            
            return self.supabase.table(table).update(edit_columns).eq(columns).execute()["data"]
        elif action == Operation.DELETE:
            return self.supabase.table(table).delete().eq(columns).execute()["data"]

    def get_cf_stack(self, chat_session_id: int) -> CloudFormationStack:
        """
        Given the chat session id, get the cf stack.
        """

        response=self.perform_column_action(
            Table.CHAT_SESSIONS, 
            Operation.READ, 
            edit_columns={"id": chat_session_id, CF_STACK_COL_NAME: f"ChatSessions.{CF_STACK_COL_NAME}"}
        )["data"]

        print(response)

        return CloudFormationStack({"":None}, "")

    def edit_entire_cf_stack(self, chat_session_id: int, new_stack: CloudFormationStack):
        pass