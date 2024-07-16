from typing import List, Union
import os
import json
from src.model.stack import CloudFormationStack, Dataset
from include.llm.claude import ClaudeClient

PROMPTS="prompts"

class Extractor:
    """
    A data extractor. Extracts and returns a dataset to fine tune on.
    """

    def __init__(self, dataset_path: str, prompts_file: Union[str, None]) -> None:
        """
        Assumes that the prompts file looks exactly like this:

        ```
        {
            "prompts" : [
                "prompt 1 corresponding to stack 1",
                "prompt 2 corresponding to stack 2",
                "prompt 3 corresponding to stack 3",
                "prompt 4 corresponding to stack 4",
                "prompt 5 corresponding to stack 5",
                ...
            ]
        }
        ```
        
        """
        self.dataset_path = dataset_path
        self.prompts_file = prompts_file
        self.claude_client = ClaudeClient()

    def extract_templates(self) -> List[CloudFormationStack]:
        """
        Extracts a list of templates from the provided directory. Assumes that the directory 
        files that end with .json are valid, disregards all others.
        """

        templates = []
        for root, _, files in os.walk(self.dataset_path):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), 'r') as f:
                        try:
                            template = json.load(f)
                            templates.append(CloudFormationStack(template, file))
                        except json.JSONDecodeError:
                            continue
        return templates

    def synthetic_generator(self, stacks: List[CloudFormationStack], gt_examples: List[str]):
        """
        Generates prompts via a gpt-4o call. If n = len(gt_examples), and m = len(stacks), 
        then the first n stacks have a corresponding prompt already provided as a ground 
        truth to be used for the remaining m - n stacks.
        
        Assumes that m > n, always.
        """

        n = len(gt_examples)
        m = len(stacks)

        if m == n:
            return

        prompt = "" # TODO load this from a file
        i=0

        while i < n:
            few_shot_prompt = f"""
            prompt: {gt_examples[i]}
            cloud formation template: {stacks[i]}
            
            """

            prompt += few_shot_prompt
            i += 1

        while i < m:
            stack_str = json.dumps(stacks[i])
            synthetic_prompt = self.claude_client.query(stack_str, prompt, False)
            gt_examples.append(synthetic_prompt)

        return gt_examples

    def get_inputs(self, stacks: List[CloudFormationStack]):
        """
        Given a list of cf stacks, bundles it into a Dataset object.
        """

        data_dict = {}

        if self.prompts_file is not None:
            # need to synthetically generate it
            pass
        else:
            with open(self.prompts_file, "r", encoding="utf8") as fp:
                prompts_obj = json.load(fp)
                prompt_list = prompts_obj[PROMPTS]
                idx = 0

                while idx < len(prompt_list):
                    data_dict[prompt_list[idx]] = stacks[idx]
                    idx += 1

        return Dataset(data_dict)

    def get_dataset(self) -> Dataset:
        """
        Given a list of cf stacks, and corresponding queries, generates a dataset.
        """
        templates = self.extract_templates()
        for i in range(10):
            print(templates[i].name)

        # dataset = self.get_inputs(templates)
