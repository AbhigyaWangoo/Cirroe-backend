from abc import ABC, abstractmethod
from src.model.stack import Dataset
from typing import Tuple, Any
from dotenv import load_dotenv
from predibase import Predibase, FinetuningConfig, DeploymentConfig

import os

load_dotenv()

# pb vars
DEFAULT_DESC = "Fine-tune some model with my dataset for my task."
DEFAULT_NAME = "cfstack ultra"
DEFAULT_EPOCHS = 5.0
DEFAULT_LR = 0.4


class AbstractFineTuner(ABC):
    """
    Abstract class for fine tuning models
    """

    def __init__(self, dataset: Dataset, epochs: float, learning_rate: float) -> None:
        self.dataset = dataset
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.finetuned_model = None

    def split(self) -> Tuple[Dataset, Dataset]:
        """
        Returns a [train, test] split.
        """
        pass

    @abstractmethod
    def finetune(self) -> Any:
        """
        Takes the dataset, and runs a finetune job. Returns the model and caches it as a var.
        """
        pass


class PredibaseFineTuner(AbstractFineTuner):
    """
    A class to finetune datasets with predibase.
    """

    def __init__(
        self,
        dataset: Dataset,
        epochs: float = DEFAULT_EPOCHS,
        learning_rate: float = DEFAULT_LR,
    ) -> None:
        super().__init__(dataset, epochs, learning_rate)
        self.api_key = os.environ.get("PB_TOKEN", "")
        self.pb = Predibase(api_token=self.api_key)

    def finetune(self, name: str = DEFAULT_NAME, desc: str = DEFAULT_DESC) -> Any:
        """
        Finetune a model with predibase
        """
        # dataset = pb.datasets.from_file("/path/tldr_dataset.csv", name="tldr_dataset")

        # Create an adapter repository
        repo = pb.repos.create(name=name, description=desc, exists_ok=True)

        # Start a fine-tuning job, blocks until training is finished
        adapter = pb.adapters.create(
            config=FinetuningConfig(base_model="mistral-7b"),
            dataset=self.dataset,  # Also accepts the dataset name as a string
            repo=repo,
            description=desc,
        )
        self.finetuned_model = adapter
        # TODO set this up for inference on predibase. Create new predibase llm object in include/llm repo

        return adapter
