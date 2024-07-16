from src.ft.extract import Extractor
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='Finetuner',
                    description='finetunes a model and evaluates it against gpt4 and claude sonnet')
    parser.add_argument('-f', '--filepath',
                    action='store_true')  # on/off flag

    args = parser.parse_args()
    dataset_fpath = args.filepath
    
    # 1. Extract dataset from files (Extractor)
    extractor = Extractor(dataset_fpath)
    extractor.

    # 2. spit dataset to json file (Extractor)

    # 3. split into test and train (Fine tuner)

    # 4. load model, dataset, and tokenize (Fine tuner)

    # 5. Run finetune (Fine tuner)

    # 6. If enabled, run evaluation (Evaluate)

    #   6.a generate predictions with gpt4 + construct action (Evaluate)

    #   6.b generate predictions with claude + construct action (Evaluate)

    #   6.c generate predictions with ft model + construct action (Evaluate)
