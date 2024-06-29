from include.llm.base import AbstractLLMClient
from src.model.stack import CloudFormationStack

BASE_PROMPT_PATH = "include/prompts/"


def prompt_with_file(
    filepath: str, prompt: str, client: AbstractLLMClient, **extra_options
) -> str:
    """
    Given the prompt file, will execute client over the prompt.
    """

    with open(filepath, "r", encoding="utf8") as fp:
        sysprompt = fp.read()
        return client.query(prompt, sys_prompt=sysprompt, **extra_options)

def stack_is_delpoyable(stack: CloudFormationStack) -> bool:
    """
    Should take the stack, and just return whether it can be deployed or not.
    """
    