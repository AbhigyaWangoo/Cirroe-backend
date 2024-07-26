from typing import Any, Union
import json
from . import base

from src.model.stack import TerraformConfig
from include.llm.base import AbstractLLMClient

from include.utils import prompt_with_file, BASE_PROMPT_PATH

CONSTRUCT_CF_PROMPT = "extract_tf_config.txt"
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

    def _extract_template(self, input: str, retries: int = 3) -> TerraformConfig:
        """
        helper fn to extract a cf template from an input
        """
        try:
            if self.test_client is None:
                self.test_client = self.claude_client

            tf_template = prompt_with_file(
                BASE_PROMPT_PATH + CONSTRUCT_CF_PROMPT,
                input,
                self.test_client,
                is_json=False,
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
