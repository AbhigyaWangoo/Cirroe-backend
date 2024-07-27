# Cirroe

## Description
Cirroe is a chatbot built to allow users to describe cloud infra in natural language, and deploy that cloud infra in seconds. Simple as that.

## Setup Instructions

### Prerequisites
Only Python (version 3.12+) is required.

### Installation
Step-by-step instructions on how to set up the project locally follow.

1. **Clone the repository:**
    ```bash
    git clone [https://github.com/username/repository.git](https://github.com/AbhigyaWangoo/Cirroe-backend.git)
    cd Cirroe-backend
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Environment Variables:**
    Create a `.env` file and add the necessary environment variables. Example:
    ```env
    CLAUDE_KEY=XXXXX
    OPENAI_API_KEY=XXXXX
    PORT=3001
    SUPABASE_API_KEY=XXXXX
    SUPABASE_URL=XXXXX
    FRONTEND_PORT=3000

    DEMO_AWS_SECRET_ACCESS_KEY=XXXXX
    DEMO_AWS_ACCESS_KEY_ID=XXXXX

    PB_TOKEN=XXXXX
    ```

5. **Run the Cirroe server:**
    ```bash
    python server.py
    ```
