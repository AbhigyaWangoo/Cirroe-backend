from abc import ABC, abstractmethod
from typing import Any

class AbstractAction(ABC):
    """
    A base class for user actions
    """

    def __init__(self) -> None:
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
        return ""
