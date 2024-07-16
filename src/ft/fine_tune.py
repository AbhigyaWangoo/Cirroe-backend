from abc import ABC, abstractmethod
from src.model.stack import Dataset
from typing import Tuple, Any
from dotenv import load_dotenv
from predibase import Predibase, FinetuningConfig, DeploymentConfig

import os

load_dotenv()

# pb vars
DEFAULT_DESC='Fine-tune some model with my dataset for my task.'

class AbstractFineTuner(ABC):
    """
    Abstract class for fine tuning models
    """
    def __init__(self, dataset: Dataset, epochs: float, learning_rate: float) -> None:
        self.dataset=dataset
        self.epochs=epochs
        self.learning_rate=learning_rate
        self.finetuned_model=None

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
    def __init__(self, dataset: Dataset, epochs: float, learning_rate: float) -> None:
        super().__init__(dataset, epochs, learning_rate)
        self.api_key = os.environ.get("PB_TOKEN", "")
        self.pb = Predibase(api_token=self.api_key)

    def finetune(self, train_dataset: Dataset, desc: str = DEFAULT_DESC) -> Any:
        """
        Finetune a model with predibase
        """
        
        # dataset = pb.datasets.from_file("/path/tldr_dataset.csv", name="tldr_dataset")

        # Create an adapter repository
        repo = pb.repos.create(name="news-summarizer-model", description="TLDR News Summarizer Experiments", exists_ok=True)

        # Start a fine-tuning job, blocks until training is finished
        adapter = pb.adapters.create(
            config=FinetuningConfig(
                base_model="mistral-7b"
            ),
            dataset=dataset, # Also accepts the dataset name as a string
            repo=repo,
            description=desc
        )
        