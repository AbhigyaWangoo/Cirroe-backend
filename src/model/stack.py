from typing import Dict, Any
from typeguard import typechecked
import json

@typechecked
class CloudFormationStack:
    """A wrapper around a cf stack template"""

    def __init__(self, template: Dict[str, Any], name: str) -> None:
        self.name = name
        self.template = template
class Dataset:
    """
    A dataset of cloudformation stacks. Used in fine tuning.
    """
    def __init__(self, data: Dict[str, CloudFormationStack]) -> None:
        self.data = data

    def write(self, json_file: str, mode: str="w"):
        """
        Writes dataset to file
        """

        with open(json_file, mode, encoding="utf8") as fp:
            for prompt in self.data:
                json_obj = {prompt: json.dumps(self.data[prompt])}
                # write json_obj to jsonl output file
                fp.write(json.dumps(json_obj) + "\n")
