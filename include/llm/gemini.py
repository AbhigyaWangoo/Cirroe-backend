from typing import List
import google.generativeai as genai
import os
from . import base

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DEFAULT_LLM = "gemini-1.5-flash"


class GeminiClient(base.AbstractLLMClient):
    """
    Client class for Gemini API
    """

    def __init__(self) -> None:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    def generate_embeddings(self, sentence: str, embedding_model: str) -> List[float]:
        return super().generate_embeddings(sentence, embedding_model)

    def query(
        self,
        prompt: str,
        temperature: int = 0.1,
        sys_prompt: str = "",
        is_json: bool = False,
    ) -> str:
        """A simple wrapper to the gemini api"""

        config = {"temperature": temperature}
        if is_json:
            config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name=DEFAULT_LLM,
            system_instruction=sys_prompt,
            generation_config=config,
        )
        response = model.generate_content(prompt)

        return response
