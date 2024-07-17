from typing import Dict, Any
from typeguard import typechecked
import json

NAME="name"
TEMPLATE="template"
PROMPT="prompt"
CF_STACK_OBJ="cf_stack_obj"

@typechecked
class CloudFormationStack:
    """A wrapper around a cf stack template"""

    def __init__(self, template: Dict[str, Any], name: str) -> None:
        self.name = name
        self.template = template
class Dataset:
    """
    A dataset of cloudformation stacks. Used in fine tuning.
    
    When in file format, it obeys the following structure:
    ```json
    {"prompt": <actual_prompt>, "cf_stack_obj": {"name": <name>, "template": <json template>}}
    {"prompt": <actual_prompt>, "cf_stack_obj": {"name": <name>, "template": <json template>}}
    {"prompt": <actual_prompt>, "cf_stack_obj": {"name": <name>, "template": <json template>}}
    {"prompt": <actual_prompt>, "cf_stack_obj": {"name": <name>, "template": <json template>}}
    ...
    ```
    """
    def __init__(self, data: Dict[str, CloudFormationStack]) -> None:
        self.data = data

    def split(self, train_vs_test: 0.8):
        pass

    def read(self, jsonl_file: str):
        """
        Reads object from jsonl file.
        """
        data = {}
        with open(jsonl_file, "r", encoding="utf8") as fp:
            while line := fp.readline():
                line_json = json.loads(line.rstrip())
                prompt = line_json[PROMPT]
                cf_stack = line_json[CF_STACK_OBJ]

                stack_name = cf_stack[NAME]
                stack_template = cf_stack[TEMPLATE]
                stack = CloudFormationStack(stack_template, stack_name)

                data[prompt] = stack

    def write(self, json_file: str, mode: str="w"):
        """
        Writes dataset to file.
        """

        with open(json_file, mode, encoding="utf8") as fp:
            for prompt in self.data:
                json_obj = {
                    PROMPT: prompt,
                    CF_STACK_OBJ: {
                        NAME: self.data[prompt][NAME],
                        TEMPLATE: self.data[prompt][TEMPLATE],
                    }
                }

                # write json_obj to jsonl output file
                fp.write(json.dumps(json_obj) + "\n")
