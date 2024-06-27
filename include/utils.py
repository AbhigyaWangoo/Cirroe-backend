from include.llm.gpt import GPTClient

BASE_PROMPT_PATH = "include/prompts/"


def prompt_with_file(
    filepath: str, prompt: str, gpt_client: GPTClient, **extra_options
) -> str:
    """
    Given the prompt file, will execute client over the prompt.
    """

    with open(filepath, "r", encoding="utf8") as fp:
        sysprompt = fp.read()
        return gpt_client.query(prompt, sys_prompt=sysprompt, **extra_options)
