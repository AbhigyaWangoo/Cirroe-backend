from include.llm.base import AbstractLLMClient
from typeguard import typechecked
import hashlib

BASE_PROMPT_PATH = "include/prompts/"
QUERY_CLASSIFIERS_BASE = "query_classifiers/"


def prompt_with_file(
    filepath: str, prompt: str, client: AbstractLLMClient, **extra_options
) -> str:
    """
    Given the prompt file, will execute client over the prompt.
    """

    with open(filepath, "r", encoding="utf8") as fp:
        sysprompt = fp.read()
        return client.query(prompt, sys_prompt=sysprompt, **extra_options)


@typechecked
def hash_str(input_string: str) -> str:
    """
    hash and return the provided string
    """
    # Create a new sha256 hash object
    sha256 = hashlib.sha256()

    # Encode the input string and update the hash object with it
    sha256.update(input_string.encode("utf-8"))

    # Get the hexadecimal representation of the hash
    hashed_string = sha256.hexdigest()

    return hashed_string
