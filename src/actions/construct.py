from typing import Any
import json
from . import base

from src.model.stack import CloudFormationStack

from include.utils import prompt_with_file, BASE_PROMPT_PATH

CONSTRUCT_CF_PROMPT="extract_cf_template.txt"

class ConstructCFStackAction(base.AbstractAction):
    """
    an action to construct a cf stack template
    """

    def __init__(self) -> None:
        super().__init__()

    def _extract_template(self, input: str) -> CloudFormationStack:
        """
        helper fn to extract a cf template from an input
        """
        cf_json = prompt_with_file(BASE_PROMPT_PATH + CONSTRUCT_CF_PROMPT, input, self.gpt_client, is_json=True)

        return CloudFormationStack(cf_json, "")

    def _verify_stack(
        self, stack: CloudFormationStack, original_query: str
    ) -> CloudFormationStack:
        """
        Verifies the provided stack is indeed handling the original query's needs or not.
        Also checks the stack against other examples to ensure the syntax is valid.
        """
        return CloudFormationStack({"": None}, "")

    def _coalesce_response(self, stack: CloudFormationStack, original_query: str) -> str:
        """
        Respond to the user abstractly in one final response. Ask them whether we should deploy,
        or whether they'd like to refine the usage.
        """
        return ""

    def trigger_action(self, infra_description: str) -> Any:
        """
        For construction a CF stack, this fn will input a
        """
        # 1. Clean up input with a gpt call.
        cleaned_input = self.clean_input(infra_description)

        # 2. Run a gpt call to extract a cf stack template
        cf_stack = self._extract_template(cleaned_input)

        # 3. Check cf stack template against original query.
        # fixed_cf_stack = self._verify_stack(cf_stack, cleaned_input)

        # 3.a persist cf stack in storage

        # 4. Return a string with the detailed info regarding the cf stack's functionality
        # return self._coalesce_response(fixed_cf_stack, infra_description)
        return ""
