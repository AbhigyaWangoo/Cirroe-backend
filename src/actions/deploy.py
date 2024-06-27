from typing import Any
from . import base

from src.model.stack import CloudFormationStack


class DeployCFStackAction(base.AbstractAction):
    """
    An action to deploy a cf stack to a user's account
    """

    def __init__(self, user_stack: CloudFormationStack, user_aws_secret_key: str, user_aws_pub_access_key: str) -> None:
        """
        Constructs a user deployment action
        """
        self.user_secret_key = user_aws_secret_key
        self.user_aws_pub_access_key = user_aws_pub_access_key
        self.user_stack = user_stack
        super().__init__()

    def trigger_action(self, input) -> Any:
        """
        Deploys user's cf stack into their account
        """
        return super().trigger_action(input)
