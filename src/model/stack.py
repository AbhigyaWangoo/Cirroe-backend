from typing import Dict, Any
from typeguard import typechecked


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