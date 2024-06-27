from typing import Dict, Any
from typeguard import typechecked


@typechecked
class CloudFormationStack:
    """A wrapper around a cf stack template"""

    def __init__(self, template: Dict[str, Any], raw_data: str) -> None:
        self.template = template
        self.raw_data = raw_data
