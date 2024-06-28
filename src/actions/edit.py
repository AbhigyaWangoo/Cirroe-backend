from typing import Any
from . import base
import json

from src.model.stack import CloudFormationStack
from include.utils import BASE_PROMPT_PATH, prompt_with_file

EDIT_STACK_PROMPT = "edit_stack.txt"
DESCRIBE_EDIT_PROMPT = "describe_edit.txt"


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
        new_stack = prompt_with_file(
            BASE_PROMPT_PATH + EDIT_STACK_PROMPT,
            user_input,
            self.gpt_client,
            is_json=True,
            temperature=0.35,
        )

        return CloudFormationStack(new_stack, "")

    def describe_changes(
        self, s1: CloudFormationStack, s2: CloudFormationStack, original_prompt: str
    ) -> str:
        """
        An appropriate response to the user regarding the edit they've made.
        """
        diff_prompt = f"""
        Original infrastructure:
        {json.dumps(s1.template)}
        
        New infrastructure:
        {json.dumps(s2.template)}
        
        User's edit reques:
        {original_prompt}
        """

        response = prompt_with_file(
            BASE_PROMPT_PATH + DESCRIBE_EDIT_PROMPT, diff_prompt, self.gpt_client
        )

        return response

    def trigger_action(self, input: str) -> Any:
        """
        In this case, triggering an edit involves taking the stack to edit,
        and returning a new one. The input should be the user's desired edit on
        the existing stack.
        """
        # 1. clean input
        new_input = self.clean_input(input)

        # 2. Determine new stack with a single gpt call to edit it
        edited_stack = self.determine_edit(new_input)

        # 3. Persist new updated stack

        # 4. Respond qualitatively to user
        return self.describe_changes(self.stack_to_edit, edited_stack, new_input)
