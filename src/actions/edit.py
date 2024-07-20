from typing import Any
from . import base
import json

from src.model.stack import TerraformConfig
from include.utils import BASE_PROMPT_PATH, prompt_with_file

EDIT_STACK_PROMPT = "edit_stack.txt"
DESCRIBE_EDIT_PROMPT = "describe_edit.txt"


class EditCFStackAction(base.AbstractAction):
    """
    An action to edit the provided stack
    """

    def __init__(self, stack_to_edit: TerraformConfig) -> None:
        super().__init__()
        self.stack_to_edit = stack_to_edit
        self.new_stack = None

    def determine_edit(self, user_input: str, retries: int = 3) -> TerraformConfig:
        """
        Alter the stack_to_edit with the provided user input, and return the new stack.
        """

        try:
            new_stack = prompt_with_file(
                BASE_PROMPT_PATH + EDIT_STACK_PROMPT,
                user_input,
                self.claude_client,
                is_json=True,
                temperature=0.35,
            )
        except Exception as e:
            print(f"Couldn't parse due to {e}. Retrying...")
            return self.determine_edit(user_input, retries - 1)

        return TerraformConfig(new_stack, str(hash(user_input)))

    def describe_changes(
        self, s1: TerraformConfig, s2: TerraformConfig, original_prompt: str
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
        new_input = input
        # new_input = self.clean_input(input)

        # 2. Determine new stack with a single gpt call to edit it
        edited_stack = self.determine_edit(new_input)

        # 3. Persist new updated stack
        self.new_stack = edited_stack

        # 4. Respond qualitatively to user
        return self.describe_changes(self.stack_to_edit, edited_stack, new_input)
