from typing import Any, Union

from . import base

from src.model.stack import TerraformConfig
from include.llm.base import AbstractLLMClient

from include.utils import prompt_with_file, BASE_PROMPT_PATH

COALESCE_CONSTRUCTION_RESPONSE = "coalesce_response.txt"


class ConstructTFConfigAction(base.AbstractAction):
    """
    An action to construct a cf stack template. Can optionally provide a
    test_client to test different models.
    """

    def __init__(self, test_client: Union[AbstractLLMClient, None] = None) -> None:
        self.tf_config = None
        self.test_client = test_client
        super().__init__()

    def get_construction_prompt(self, user_query: str) -> str:
        """
        Constructs a construction prompt from the provided user query
        """
        return f"""
        You are a skilled cloud engineer tasked with creating a Terraform configuration file based on a user's description. Your goal is to construct a complete, deployable Terraform template that matches the described architecture's functionality.
        Assume that if the user does not describe some resource, it does not exist. You must create everything from complete scratch.

        Here is the description of the Terraform template to be created:
        <terraform_description>
        {user_query}
        </terraform_description>

        Follow these steps to create the Terraform configuration:

        1. Carefully analyze the provided description to identify all required resources and their relationships.
        2. Create a terraform configuration file with all necessary resource blocks and their configurations.
        3. Include any required provider blocks at the beginning of the file.
        4. Create and use all dependent resources necessary to ensure the template is deployable.
        5. Choose appropriate resource names that reflect their purpose in the architecture.
        6. If you are unsure about any resource values, use 'xxxxxx' to denote an unknown value.
        7. Ensure all resources are properly linked and dependencies are correctly specified.

        Your output must be in perfect Terraform configuration file format. Do not include any comments or any text that would violate Terraform syntax. The output should be ready to be loaded into a file and run without any modifications.

        Remember:
        - Do not output anything except for the Terraform code.
        - Do not include any explanations, comments, or additional text.
        - Ensure the configuration is as complete as possible based on the given description.
        - Use 'xxxxxx' for any values that are not specified in the description or that you're unsure about.

        Begin your output with the provider block (if necessary) and continue with the resource blocks. Do not include any other text or formatting outside of the Terraform configuration syntax.
        """

    def _extract_template(self, input: str, retries: int = 3) -> TerraformConfig:
        """
        helper fn to extract a cf template from an input
        """
        try:
            if self.test_client is None:
                self.test_client = self.claude_client

            tf_template = self.claude_client.query(
                self.get_construction_prompt(input), "", False, temperature=0.8
            )
        except Exception as e:
            print(f"Couldn't extract config because of {e}. Retrying...")

            return self._extract_template(input, retries - 1)

        return TerraformConfig(
            tf_template, str(hash(input))
        )  # TODO need to figure out how to get this value somehow

    def _coalesce_response(self, stack: TerraformConfig, original_query: str) -> str:
        """
        Respond to the user abstractly in one final response. Ask them whether we should deploy,
        or whether they'd like to refine the usage. Additionlally, if we need any clarifications or
        additional info, we need to include that in the response.
        """

        prompt = f"""
            Original query:
            {original_query}

            Constructed terraform configuration: 
            {stack.template}
        """

        response = prompt_with_file(
            BASE_PROMPT_PATH + COALESCE_CONSTRUCTION_RESPONSE, prompt, self.gpt_client
        )

        return response

    def trigger_action(self, infra_description: str) -> Any:
        """
        For construction of a tf config file, this fn will input a response,
        and create + update a config in supabase.
        """
        # 1. Clean up input with a gpt call.
        cleaned_input = self.clean_input(infra_description)
        # print(cleaned_input)

        # 2. Run a gpt call to extract a terraform config
        tf_config = self._extract_template(cleaned_input)
        print(tf_config.template)

        # 3. Check terraform config against original query. Removing for now.
        self.tf_config = tf_config

        # 4. Return a string with the detailed info regarding the terraform config's functionality
        return self._coalesce_response(tf_config, infra_description)
