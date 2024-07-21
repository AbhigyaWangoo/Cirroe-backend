from typing import List, Union, Dict, Tuple
import os
import json
from src.model.stack import TerraformConfig, Dataset, NAME, PROMPT
from include.llm.claude import ClaudeClient
from include.llm.gpt import GPTClient
from include.utils import BASE_PROMPT_PATH
from typeguard import typechecked

PROMPTS=PROMPT+"s"


SYNTHETIC_EXTRACTOR_PROMPT="extrapolate_synthetic.txt"
EXAMPLES_FPATH="include/data/prompt_examples.json"

class Extractor:
    """
    A data extractor. Extracts and returns a dataset to fine tune on.
    """

    def __init__(self, dataset_path: str, prompts_file: Union[str, None] = None) -> None:
        """
        Assumes that the prompts file looks exactly like this:

        ```json
        {
            "prompts" : [
                {
                    "prompt": "prompt 1 corresponding to stack 1",
                    "name": "name of file 1 in dataset"
                },
                {
                    "prompt": "prompt 2 corresponding to stack 2",
                    "name": "name of file 2 in dataset"
                },
                {
                    "prompt": "prompt 3 corresponding to stack 3",
                    "name": "name of file 3 in dataset"
                },
                ...
            ]
        }
        ```
        """

        self.dataset_path = dataset_path
        self.prompts_file = prompts_file
        self.claude_client = GPTClient()

    def extract_templates(self) -> List[TerraformConfig]:
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
                            templates.append(TerraformConfig(template, file))
                        except json.JSONDecodeError:
                            continue
        return templates

    @typechecked
    def synthetic_generator(self,
                            stacks: Dict[str, TerraformConfig],
                            gt_examples: List[Dict[str,str]]) -> Dict[str, TerraformConfig]:
        """
        Generates prompts via a gpt-4o call. If n = len(gt_examples), and m = len(stacks), 
        then the first n stacks have a corresponding prompt already provided as a ground 
        truth to be used for the remaining m - n stacks.

        Assumes that m > n, always.
        
        stacks:
        ```json
        {
            "Portfolio.json": <stack>,
            "Product.json": <stack>,
            "compliant-bucket.json": <stack>
        }
        ```

        gt_examples: 
        ```json
        [
            {
                "prompt": "Can you create a Service Catalog portfolio called Test_Portfolio? The dept is 1234, and the account id of the child aws account is 1234567890",
                "name": "Portfolio.json"
            },
            {
                "prompt": "Create an AWS CloudFormation template for a Service Catalog Product, the distributor should be 'App Vendor', and the support email 'https://www.support.example.com'",
                "name": "Product.json"
            },
            {
                "prompt": "Can you create an AWS CloudFormation template for an S3 bucket with server-side encryption, versioning enabled, and all public access blocked? The bucket should also have replication to another bucket and logging enabled.",
                "name": "compliant-bucket.json"
            },
        ]
        ```
        """

        n = len(gt_examples)
        m = len(stacks)

        if m == n:
            return

        prompt_to_stack_mapping={}

        with open(BASE_PROMPT_PATH + SYNTHETIC_EXTRACTOR_PROMPT, "r", encoding="utf8") as fp:
            prompt = fp.read()
            i=0
            covered_fnames = set()

            while i < n:
                prompt_example = gt_examples[i][PROMPT]
                file_name = gt_examples[i][NAME]
                covered_fnames.add(file_name)

                few_shot_prompt = f"""
                prompt: {prompt_example}
                cloud formation template: {stacks[file_name].template}
                """

                prompt_to_stack_mapping[prompt_example] = stacks[file_name]
                prompt += few_shot_prompt
                i += 1

            flag=True
            for fname in stacks:
                if fname not in covered_fnames:
                    stack_str = json.dumps(stacks[fname].template)

                    synthetic_prompt="aaa"+fname
                    if flag:
                        synthetic_prompt = self.claude_client.query(prompt=stack_str, sys_prompt=prompt)
                        print(synthetic_prompt)
                        print(fname)
                        flag=False

                    prompt_to_stack_mapping[synthetic_prompt] = stacks[fname]

        return prompt_to_stack_mapping

    @typechecked
    def get_inputs(self, stacks: List[TerraformConfig], gt_examples: List[Dict[str,str]]) -> Dataset:
        """
        Given a list of cf stacks, bundles it into a Dataset object.
        """
        stack_dict = {stack.name: stack for stack in stacks}
        if self.prompts_file is None:
            # need to synthetically generate it
            dataset = self.synthetic_generator(stack_dict, gt_examples)
            print("synthetically generating")
            # print(dataset.keys())
            return Dataset(dataset)

        # prompts already exist from before.
        print("prompt exists from before")
        data_dict = {}
        prompt_list: List[str]
        idx = 0
        with open(self.prompts_file, "r", encoding="utf8") as fp:
            prompts_obj = json.load(fp)
            prompt_list = prompts_obj[PROMPTS]

        while idx < len(prompt_list):
            file_name = prompt_list[idx][NAME]
            data_dict[prompt_list[idx][PROMPT]] = stack_dict[file_name]
            idx += 1

        return Dataset(data_dict)

    def get_dataset(self) -> Dataset:
        """
        Given a list of cf stacks, and corresponding queries, generates a dataset.
        """
        templates = self.extract_templates()
        # for i in range(10):
        #     print(templates[i].name)

        with open(EXAMPLES_FPATH, "r", encoding="utf8") as fp:
            gt_examples=json.load(fp)

            dataset = self.get_inputs(templates, gt_examples[PROMPTS])

            return dataset

    def split(self, dataset: Dataset, train_vs_test: float = 0.8) -> Tuple[Dataset, Dataset]:
        """
        Split a dataset into train and test by randomly selecting
        values for train and test. Return both.
        """
        train = {}
        test = {}

        return Dataset(train), Dataset(test)
