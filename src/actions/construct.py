from typing import Any, Union
import json
from . import base

from src.model.stack import CloudFormationStack
from include.llm.base import AbstractLLMClient

from include.utils import prompt_with_file, BASE_PROMPT_PATH

CONSTRUCT_CF_PROMPT = "extract_cf_template.txt"
COALESCE_CONSTRUCTION_RESPONSE = "coalesce_response.txt"
VERIFY_CONSTRUCTED_STACK = "verify_stack.txt"


class ConstructCFStackAction(base.AbstractAction):
    """
    An action to construct a cf stack template. Can optionally provide a 
    test_client to test different models.
    """

    def __init__(self, test_client: Union[AbstractLLMClient, None] = None) -> None:
        self.stack = None
        self.test_client = test_client
        super().__init__()

    def _extract_template(self, input: str, retries: int = 3) -> CloudFormationStack:
        """
        helper fn to extract a cf template from an input
        """
        try:
            if self.test_client is None:
                self.test_client = self.claude_client

            cf_json = prompt_with_file(
                BASE_PROMPT_PATH + CONSTRUCT_CF_PROMPT,
                input,
                self.test_client,
                is_json=True,
            )
        except Exception as e:
            print(f"Couldn't extract template because of {e}. Retrying...")

            return self._extract_template(input, retries - 1)

        return CloudFormationStack(cf_json, str(hash(input)))

    def _coalesce_response(
        self, stack: CloudFormationStack, original_query: str
    ) -> str:
        """
        Respond to the user abstractly in one final response. Ask them whether we should deploy,
        or whether they'd like to refine the usage. Additionlally, if we need any clarifications or
        additional info, we need to include that in the response.
        """

        prompt = f"""
            Original query:
            {original_query}

            Constructed stack: 
            {json.dumps(stack.template)}
        """

        response = prompt_with_file(
            BASE_PROMPT_PATH + COALESCE_CONSTRUCTION_RESPONSE, prompt, self.gpt_client
        )

        return response

    def trigger_action(self, infra_description: str) -> Any:
        """
        For construction a CF stack, this fn will input a response, and create + update a stack in supabase.
        """
        # 1. Clean up input with a gpt call.
        cleaned_input = self.clean_input(infra_description)
        # print(cleaned_input)

        # 2. Run a gpt call to extract a cf stack template
        cf_stack = self._extract_template(cleaned_input)
        print(cf_stack.template)

        # 3. Check cf stack template against original query. Removing for now.
        self.stack = cf_stack

        # 3.a TODO persist cf stack in storage (async ideally)

        # 4. Return a string with the detailed info regarding the cf stack's functionality
        return self._coalesce_response(cf_stack, infra_description)
