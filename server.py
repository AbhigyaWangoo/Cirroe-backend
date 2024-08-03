import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID

from src.server.wrappers import query_wrapper, deploy_wrapper, destroy_wrapper

load_dotenv()

app = FastAPI()


# Define request models
class QueryRequest(BaseModel):
    user_query: str
    user_id: UUID
    chat_session_id: UUID


class DeployRequest(BaseModel):
    user_id: UUID
    chat_session_id: UUID


class DestroyRequest(BaseModel):
    user_id: UUID
    chat_session_id: UUID


# Synchronous endpoints
@app.post("/query")
def query(request: QueryRequest):
    return {
        "result": query_wrapper(
            request.user_query, request.user_id, request.chat_session_id
        )
    }


@app.post("/deploy")
def deploy(request: DeployRequest):
    return {"result": deploy_wrapper(request.user_id, request.chat_session_id)}


@app.post("/destroy")
def destroy(request: DestroyRequest):
    return {"result": destroy_wrapper(request.user_id, request.chat_session_id)}


# Asynchronous endpoints
@app.post("/query_async")
async def query_async(request: QueryRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        query_wrapper, request.user_query, request.user_id, request.chat_session_id
    )
    return {"status": "Query task has been started in the background"}


@app.post("/deploy_async")
async def deploy_async(request: DeployRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(deploy_wrapper, request.user_id, request.chat_session_id)
    return {"status": "Deploy task has been started in the background"}


@app.post("/destroy_async")
async def destroy_async(request: DestroyRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(destroy_wrapper, request.user_id, request.chat_session_id)
    return {"status": "Destroy task has been started in the background"}


# Main entry point to run the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    frontend_port = int(os.getenv("FRONTEND_PORT", 8000))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://localhost:{frontend_port}"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(app, host="0.0.0.0", port=port)
