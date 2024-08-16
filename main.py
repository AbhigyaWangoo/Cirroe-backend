from fastapi import FastAPI
from dotenv import load_dotenv
from uuid import UUID

from src.server.wrappers import query_wrapper, deploy_wrapper, destroy_wrapper

load_dotenv()

app = FastAPI()


# Synchronous endpoints
@app.get("/query")
def query(user_query: str, user_id: str, chat_session_id: str):
    user_uuid = UUID(user_id)
    chat_session_uuid = UUID(chat_session_id.strip())
    return {"result": query_wrapper(user_query, user_uuid, chat_session_uuid)}


@app.get("/deploy")
def deploy(user_id: str, chat_session_id: str):
    user_uuid = UUID(user_id)
    chat_session_uuid = UUID(chat_session_id.strip())
    return {"result": deploy_wrapper(user_uuid, chat_session_uuid)}


@app.get("/destroy")
def destroy(user_id: str, chat_session_id: str):
    user_uuid = UUID(user_id)
    chat_session_uuid = UUID(chat_session_id.strip())
    return {"result": destroy_wrapper(user_uuid, chat_session_uuid)}
