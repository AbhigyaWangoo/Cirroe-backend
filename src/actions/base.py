from abc import ABC, abstractmethod
from typing import Any

from include.llm.gpt import GPTClient
from include.utils import prompt_with_file

CLEAN_INPUT_PROMPT = "include/prompts/clean_input.txt"

class AbstractAction(ABC):
    """
    A base class for user actions
    """

    def __init__(self) -> None:
        self.gpt_client = GPTClient()
        super().__init__()

    @abstractmethod
    def trigger_action(self, input) -> Any:
        """
        The standard entrypoint fn to trigger all actions.
        """
        pass

    def clean_input(self, input: str) -> str:
        """
        helper fn to clean userinput to get a good input to template construction
        """
        return prompt_with_file(CLEAN_INPUT_PROMPT, input, self.gpt_client)
