from abc import ABC, abstractmethod

from typing import List


class AbstractLLMClient(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def query(sys_prompt: str, prompt: str) -> str:
        pass

    @abstractmethod
    def generate_embeddings(self, sentence: str, embedding_model: str) -> List[float]:
        pass
