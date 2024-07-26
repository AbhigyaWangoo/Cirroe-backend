from src.actions.construct import ConstructTFConfigAction
from src.model.stack import Dataset
from include.llm.base import AbstractLLMClient
from typing import List


class EvaluationResult:
    """
    A test run results bundle.
    """

    def __init__(self) -> None:
        pass

    def print_results(self) -> str:
        """
        Print results and return the str associated.
        """
        return ""

    def save_results(self, output_file: str):
        """
        Save results of a run to a file.
        """
        str_results = self.print_results()

        with open(output_file, "w", encoding="utf8") as fp:
            fp.write(str_results)


class Evaluator:
    """
    A class meant to evaluate different llms against the cf stack construction
    action. Evaluates against the provided test_dataset
    """

    def __init__(self, models: List[AbstractLLMClient], test_dataset: Dataset) -> None:
        self.models = models
        self.test_dataset = test_dataset

    def evaluate(self) -> EvaluationResult:
        """
        Evaluates all the provided models against the test dataset.
        """
        return EvaluationResult()
