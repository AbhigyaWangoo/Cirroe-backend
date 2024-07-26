from src.ft.extract import Extractor
from src.ft.fine_tune import PredibaseFineTuner
from src.ft.evaluate import Evaluator

from include.llm.claude import ClaudeClient
from include.llm.gpt import GPTClient

from src.model.stack import Dataset
import argparse
import os

CURATED_DATASET_PATH = "data/generated_dataset.jsonl"

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(
    #                 prog='Finetuner',
    #                 description='finetunes a model and evaluates it against gpt4 and claude sonnet')
    # parser.add_argument('-f', '--filepath',
    #                 action='store_true')  # on/off flag

    # args = parser.parse_args()
    # dataset_fpath = args.filepath
    evaluate = False
    dataset_fpath = "include/cfrepo"

    # 1. Extract dataset from files (Extractor)
    extractor = Extractor(dataset_fpath)
    dataset = Dataset(None)
    if not os.path.exists(CURATED_DATASET_PATH):
        dataset = extractor.get_dataset()

        # 2. spit dataset to json file (Extractor)
        dataset.write(CURATED_DATASET_PATH)
    else:
        dataset.read(CURATED_DATASET_PATH)

    # 3. split into test and train (Fine tuner)
    train, test = extractor.split(dataset)

    # 4. load model, train, and tokenize (Fine tuner)
    pft = PredibaseFineTuner(train)

    # 5. Run finetune (Fine tuner)
    adapter = pft.finetune()

    # 6. If enabled, run evaluation (Evaluate)
    if evaluate:
        # 6.a generate predictions with gpt4 + construct action (Evaluate)
        # 6.b generate predictions with claude + construct action (Evaluate)
        # 6.c generate predictions with ft model + construct action (Evaluate)
        evaluator = Evaluator([adapter, GPTClient(), ClaudeClient()], test)

        result = evaluator.evaluate()

        result.save_results("include/data/evaluation_results.txt")
