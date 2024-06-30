from typing import List
from . import base
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

API_KEY = os.environ["CLAUDE_KEY"]
MODEL = "claude-3-5-sonnet-20240620"
MAX_TOKENS = 1024

if API_KEY is None:
    print("Please set the CLAUDE_KEY env var in the .env file")
    exit(1)


class ClaudeClient(base.AbstractLLMClient):
    """A client module to call the mistral API"""

    def __init__(self) -> None:
        super().__init__()
        self._client = anthropic.Client(api_key=API_KEY)

    def generate_embeddings(self, sentence: str, embedding_model: str) -> List[float]:
        return super().generate_embeddings(sentence, embedding_model)

    def query(
        self, prompt: str, sys_prompt: str, model: str = MODEL, temperature: int = 0.2
    ) -> str:
        """A simple wrapper to the claude api"""

        response = self._client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=4096,
            system=sys_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        # max_tokens=1024,

        return response.content[0].text
