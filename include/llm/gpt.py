from openai import OpenAI
import json
from dotenv import load_dotenv
import os
from . import base
from typing import List

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    print("Please pass in OPENAI_API_KEY in the .env file")
    exit(1)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_LLM = "gpt-4o"
JSON_COMPATIBLE_LLM = "gpt-4-1106-preview"

EMBEDDING_TO_DIMENSION = {
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    "text-embedding-3-large": 3072,
}


class GPTClient(base.AbstractLLMClient):
    """A client module to call the GPT API"""

    def __init__(self) -> None:
        super().__init__()

        self._client = OpenAI(api_key=OPENAI_API_KEY)

    def generate_embeddings(
        self, sentence: str, embedding_model: str = DEFAULT_EMBEDDING_MODEL
    ) -> List[float]:
        """
        Use the OpenAI API to generate embeddings for the provided string.
        """
        try:
            response = self._client.embeddings.create(
                model=embedding_model, input=sentence
            )
            embeddings = response.data[0].embedding

            return embeddings
        except Exception as e:
            return str(e)

    def query(
        self,
        prompt: str,
        engine: str = DEFAULT_LLM,
        temperature: int = 0.1,
        sys_prompt: str = None,
        is_json: bool = False,
    ) -> str:
        """A simple wrapper to the gpt api"""

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        if sys_prompt is not None:
            messages.append(
                {
                    "role": "system",
                    "content": sys_prompt,
                }
            )

        client_kwargs = {
            "messages": messages,
            "model": engine,
            "temperature": temperature,
        }

        if is_json:
            client_kwargs["response_format"] = {"type": "json_object"}
            client_kwargs["model"] = JSON_COMPATIBLE_LLM

        response = self._client.chat.completions.create(**client_kwargs)

        generated_response = response.choices[0].message.content.strip()

        if is_json:
            return json.loads(generated_response)

        return generated_response
