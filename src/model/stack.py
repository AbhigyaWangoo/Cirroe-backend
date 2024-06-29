from typing import Dict, Any
from typeguard import typechecked


@typechecked
class CloudFormationStack:
    """A wrapper around a cf stack template"""

    def __init__(self, template: Dict[str, Any]) -> None:
        self.template = template
