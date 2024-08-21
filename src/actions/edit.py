from typing import Any
from . import base
import json

from src.model.stack import TerraformConfig
from include.utils import BASE_PROMPT_PATH, prompt_with_file

EDIT_CONFIG_EXAMPLES = "edit_stack_examples.txt"
DESCRIBE_EDIT_PROMPT = "describe_edit.txt"


class EditTFConfigAction(base.AbstractAction):
    """
    An action to edit the provided config
    """

    def __init__(self, config_to_edit: TerraformConfig) -> None:
        super().__init__()
        self.config_to_edit = config_to_edit
        self.new_config = None

    def get_structured_edit_prompt(self, query: str) -> str:
        """
        Get a very carefully structured sysprompt for stack edits
        """

        examples = ""
        with open(BASE_PROMPT_PATH + EDIT_CONFIG_EXAMPLES, "r", encoding="utf8") as fp:
            examples += fp.read()

        sysprompt = f"""
        You are an AI assistant tasked with modifying a Terraform file based on a user's requested change. Follow these instructions carefully:

        1. First, you will be presented with a Terraform file

        2. Next, you will be given a desired change in the architecture

        3. Analyze the desired change carefully. Determine if it requires modifications to the Terraform file. If the change request is unclear or doesn't necessitate alterations to the architecture, do not modify the file.

        4. If modifications are needed, make only the changes explicitly requested by the user. Do not make any additional edits or improvements that weren't specifically asked for.

        5. Output the modified Terraform file. If no changes were necessary, output the original file unchanged. Your output should contain only valid Terraform code, without any additional comments, explanations, or formatting that would violate the Terraform file format. The output should be deployable via Terraform without any issues.

        Remember:
        - Only make changes explicitly requested by the user.
        - Do not add any comments or explanations to the Terraform file.
        - Ensure the output is a valid Terraform file that can be deployed without issues.
        - Do not include any text before or after the Terraform file content in your output.
        - If anything is marked with an 'xxxxxx', that means that specific information is missing and is needed for a complete terraform file.

        Here is an example:

        {examples}

        Here is the actual terraform file to analyze:
        <terraform_file>
        {self.config_to_edit}
        </terraform_file>

        And here is the desired change in architecture:
        <desired_change>
        {query}
        </desired_change>
        """

        return sysprompt

    def determine_edit(self, user_input: str, retries: int = 3) -> TerraformConfig:
        """
        Alter the config_to_edit with the provided user input, and return the new config.
        """

        try:
            sys_prompt = self.get_structured_edit_prompt(user_input)

            new_config = self.claude_client.query(
                user_input, sys_prompt, is_json=False, temperature=0.7
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
