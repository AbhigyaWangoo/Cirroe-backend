from typing import Any
from . import base
import json

from src.model.stack import TerraformConfig
from include.utils import BASE_PROMPT_PATH, prompt_with_file

EDIT_CONFIG_PROMPT = "edit_stack.txt"
DESCRIBE_EDIT_PROMPT = "describe_edit.txt"


class EditTFConfigAction(base.AbstractAction):
    """
    An action to edit the provided config
    """

    def __init__(self, config_to_edit: TerraformConfig) -> None:
        super().__init__()
        self.config_to_edit = config_to_edit
        self.new_config = None

    def determine_edit(self, user_input: str, retries: int = 3) -> TerraformConfig:
        """
        Alter the config_to_edit with the provided user input, and return the new config.
        """

        try:
            new_config = prompt_with_file(
                BASE_PROMPT_PATH + EDIT_CONFIG_PROMPT,
                user_input,
                self.claude_client,
                is_json=False,
                temperature=0.35,
            )
        except Exception as e:
            print(f"Couldn't parse due to {e}. Retrying...")
            return self.determine_edit(user_input, retries - 1)

        return TerraformConfig(new_config, self.config_to_edit.name)

    def describe_changes(
        self, s1: TerraformConfig, s2: TerraformConfig, original_prompt: str
    ) -> str:
        """
        An appropriate response to the user regarding the edit they've made.
        """
        diff_prompt = f"""
        Original infrastructure:
        {s1.template}
        
        New infrastructure:
        {s2.template}
        
        User's edit request:
        {original_prompt}
        """

        response = prompt_with_file(
            BASE_PROMPT_PATH + DESCRIBE_EDIT_PROMPT, diff_prompt, self.gpt_client
        )

        return response

    def trigger_action(self, input: str) -> Any:
        """
        In this case, triggering an edit involves taking the config to edit,
        and returning a new one. The input should be the user's desired edit on
        the existing config.
        """
        # 1. clean input
        new_input = input
        # new_input = self.clean_input(input)

        # 2. Determine new config with a single gpt call to edit it
        edited_config = self.determine_edit(new_input)

        # 3. Persist new updated config
        self.new_config = edited_config

        # 4. Respond qualitatively to user
        return self.describe_changes(self.config_to_edit, edited_config, new_input)
