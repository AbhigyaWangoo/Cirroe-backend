import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from src.server.wrappers import query_wrapper, deploy_wrapper

load_dotenv()

app = FastAPI()

DEV_MOCK_MSG = """
# Instructions for Testing the Chat Application

## Step 1: Setting Up the Environment
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/chat-application.git
"""

DEPLOYMENT_MOCK_MSG = """
Huzzah! Your deployment succeeded. Here's a link you can access it at: 
"""


# Define request models
class QueryRequest(BaseModel):
    user_query: str
    user_id: int
    chat_session_id: int


class DeployRequest(BaseModel):
    user_id: int
    chat_session_id: int


# Synchronous endpoints
@app.post("/query")
def query(request: QueryRequest):
    return {"result": DEV_MOCK_MSG}


@app.post("/deploy")
def deploy(request: DeployRequest):
    import time

    time.sleep(20)
    # return {"result": DEV_MOCK_MSG}


# Asynchronous endpoints
@app.post("/query_async")
async def query_async(request: QueryRequest, background_tasks: BackgroundTasks):
    # background_tasks.add_task(query_wrapper, request.user_query, request.user_id, request.chat_session_id)
    return {
        "status": "Query task has been started in the background (not really. This is dev)"
    }


@app.post("/deploy_async")
async def deploy_async(request: DeployRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(deploy_wrapper, request.user_id, request.chat_session_id)
    return {
        "status": "Deploy task has been started in the background (not really. This is dev)"
    }


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
