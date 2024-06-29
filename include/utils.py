from include.llm.base import AbstractLLMClient

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
