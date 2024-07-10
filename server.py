import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import time
import random

from src.server.wrappers import query_wrapper, deploy_wrapper

from src.actions.deploy import DeployCFStackAction
from src.model.stack import CloudFormationStack
from src.db.supa import SupaClient

load_dotenv()

app = FastAPI()

# I would like to setup a Kubernetes cluster with amazon EKS, with each container running an nginx server. Please set this up in us-west-1 for me.

DEV_MOCK_MSGS = ["""
The infrastructure you requested will set up a Kubernetes cluster using Amazon EKS in the us-west-1 region, with each container running an NGINX server. Here's a breakdown of the solution:

1. **Amazon EKS Cluster**: This creates a managed Kubernetes cluster, which simplifies running Kubernetes applications on AWS without needing to install and operate your own Kubernetes control plane.

2. **Node Group**: This provisions and manages a set of Amazon EC2 instances to run your Kubernetes applications. The instances are automatically distributed across multiple subnets for high availability.

3. **NGINX Server Pods**: Each Kubernetes pod will run an NGINX server, allowing you to serve web content or act as a reverse proxy for your applications.

Before proceeding with deployment, I need the following additional information:
- The Subnet IDs in which you want to deploy the EKS cluster.
- The IAM Role ARNs for the EKS Cluster and Node Group, which must have the necessary permissions.

Would you like to make any edits to the proposed infrastructure? For example, adjustments to instance types, desired node count, or specific configurations for the NGINX containers? Let me know if there are any other requirements or preferences you have.
""",
"""
Based on your requirements, I've updated the infrastructure setup to include the creation of a new subnet and configured the node group to have a total of 5 nodes. Here's an overview of the updated setup:

***Amazon EKS Cluster***: This will create a managed Kubernetes cluster in the us-west-1 region.

***New Subnet***: A new subnet will be created specifically for this EKS cluster.

***Node Group***: This will provision and manage a total of 5 Amazon EC2 instances to run your Kubernetes applications.

***NGINX Server Pods***: Each Kubernetes pod will run an NGINX server.

***Custom IAM role***: We'll go ahead and create a new custom IAM role to access the cluster.

Also, us-west-1 can't be used to create subnets, I suggest using us-east-1 instead. Can I proceed in that region?
""",
"""
Thank you! Also, we'll need to use an AWS Lambda-backed custom resource for the Kubernetes manifest. 
We'll also include the necessary Lambda function for deploying the Kubernetes manifest. Is that ok?
""",
"""
Alright, if that's all, then we should be ready to deploy! If you'd like to specify any other parameters, then please let me know, 
otherwise please press the deploy button.
"""
]

DEPLOYMENT_DEMO_RESPONSE="""
The infrastructure has been successfully deployed! Here are the details:

***Amazon EKS Cluster:*** A managed Kubernetes cluster has been created in the us-east-1 region.
***Node Group:*** A node group with 5 Amazon EC2 instances has been provisioned to run your Kubernetes applications.
***NGINX Server Pods:*** Each Kubernetes pod is running an NGINX server.
You can access your Kubernetes cluster using the AWS Management Console or the AWS CLI. To interact with the cluster, ensure you have kubectl installed and configured. Here's how you can get started:

Connect to the EKS Cluster:
```
aws eks --region us-east-1 update-kubeconfig --name eks-cluster
```

Verify the Nodes:
```
kubectl get nodes
```

Access NGINX Pods:
```
kubectl get pods -o wide
```

Your NGINX servers are up and running, ready to serve web content or act as reverse proxies. Happy deploying!
"""


DEMO_SECRET=os.environ.get("DEMO_AWS_SECRET_ACCESS_KEY", None)
DEMO_KEY_ID=os.environ.get("DEMO_AWS_ACCESS_KEY_ID", None)

mock_msg_idx=0

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
    global mock_msg_idx
    res = {"result": DEV_MOCK_MSGS[mock_msg_idx]}
    mock_msg_idx = (mock_msg_idx + 1) % len(DEV_MOCK_MSGS)
    time.sleep(random.randint(2, 5))
    return res

@app.post("/deploy")
def deploy(request: DeployRequest):
    with open("test.json", "r", encoding="utf8") as fp:
        template = json.load(fp)
        name="eks-cluster"
        stack=CloudFormationStack(template, name)
        client = SupaClient(3)
        deploy_action = DeployCFStackAction(stack, 10, client, DEMO_SECRET, DEMO_KEY_ID)

        print("triggering")
        deploy_action.trigger_action()
        print("triggered")

        return {"result": DEPLOYMENT_DEMO_RESPONSE}

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
    mock_msg_idx = 0

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://localhost:{frontend_port}"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(app, host="0.0.0.0", port=port)
