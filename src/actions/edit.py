from typing import Any
from . import base

from src.model.stack import CloudFormationStack


class EditCFStackAction(base.AbstractAction):
    """
    An action to edit the provided stack
    """

    def __init__(self, stack_to_edit: CloudFormationStack) -> None:
        super().__init__()
        self.stack_to_edit = stack_to_edit

    def determine_edit(self, user_input: str) -> CloudFormationStack:
        """
        Alter the stack_to_edit with the provided user input, and return the new stack.
        """
        return CloudFormationStack({"": None}, "")

    def trigger_action(self, input) -> Any:
        """
        In this case, triggering an edit involves taking the stack to edit,
        and returning a new one. The input should be the user's desired edit on
        the existing stack
        """
        # 1. clean input
        new_input = self.clean_input(input)

        # 2. Determine new stack with a single gpt call to edit it
        return self.determine_edit(new_input)
