from abc import ABC, abstractmethod

from typing import List


class AbstractLLMClient(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def query(
        self,
        prompt: str,
        sys_prompt: str,
        model: str,
        is_json: bool,
        temperature: int = 0.2,
    ) -> str:
        pass

    @abstractmethod
    def generate_embeddings(self, sentence: str, embedding_model: str) -> List[float]:
        pass
