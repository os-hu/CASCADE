import torch
from DocChecker.utils import inference
import tree_sitter_languages
import json
from tqdm import tqdm


def build_data():
    with open("DocCheckerReproduction/clean_test_ids.json") as f1:
        clean_test_ids = json.load(f1)

    print(len(clean_test_ids))

    test_set = []
    with open("DocCheckerReproduction/test1.json") as f2:
        t = json.load(f2)
        test_set.extend(t)
    with open("DocCheckerReproduction/test2.json") as f2:
        t = json.load(f2)
        test_set.extend(t)
    with open("DocCheckerReproduction/test3.json") as f2:
        t = json.load(f2)
        test_set.extend(t)

    clean_test_set = []
    for t in test_set:
        if t['id'] in clean_test_ids:
            example = {}
            example['id'] = t['id']
            example["label"] = "Positive" if t['label'] == 1 else "Negative"
            example["code"] = t["new_code_raw"]
            example["doc"] = t["old_comment_raw"]

            tmp = example["code"].split("\n")
            tmp.insert(1, "// " +  example["doc"])
            example["target"] = "\n".join(tmp)
            clean_test_set.append(example)

    with open("DocCheckerReproduction/clean_test_set.json", "w") as f:
        json.dump(clean_test_set, f)



def make_predictions():
    with open("DocCheckerReproduction/clean_test_set.json") as f:
        test_set = json.load(f)

    predictions = []
    for e in tqdm(test_set):
        sample = {"id": e["id"], "label": e["label"]}
        try:
            inference(raw_code=e["target"], language="java", output_file_path="DocCheckerReproduction/prediction.json")
            with open("DocCheckerReproduction/prediction.json") as f:
                prediction = json.load(f)
                sample["prediction"] = prediction[0]["predict"]

        except:
            with open("DocCheckerReproduction/prediction.json", "w") as f:
                sample["prediction"] = "Error"


        predictions.append(sample)

    with open("DocCheckerReproduction/reproduction.json", "w") as f:
        json.dump(predictions, f)


def evaluate():
    with open("DocCheckerReproduction/reproduction.json") as f:
        predictions = json.load(f)

    evaluation = {"TP": 0, "TN": 0, "FP": 0, "FN": 0, "Error": 0}
    for p in predictions:
        if p["label"] == "Positive" and p["prediction"] == "Inconsistent!":
            evaluation["TP"] += 1
        elif p["label"] == "Positive" and p["prediction"] == "Consistent!":
            evaluation["FP"] += 1
        elif p["label"] == "Negative" and p["prediction"] == "Inconsistent!":
            evaluation["FN"] += 1
        elif p["label"] == "Negative" and p["prediction"] == "Consistent!":
            evaluation["TN"] += 1
        elif p["prediction"]   == "Error":
            evaluation["Error"] += 1


    # calculate precision recall f1 and accuracy
    precision = evaluation["TP"] / (evaluation["TP"] + evaluation["FP"])
    recall = evaluation["TP"] / (evaluation["TP"] + evaluation["FN"])
    f1 = 2 * precision * recall / (precision + recall)
    accuracy = (evaluation["TP"] + evaluation["TN"]) / (evaluation["TP"] + evaluation["TN"] + evaluation["FP"] + evaluation["FN"])

    # print metrics
    print(evaluation)
    print("Precision: ", precision)
    print("Recall: ", recall)
    print("F1: ", f1)
    print("Accuracy: ", accuracy)


if __name__ == '__main__':
    # this is used to check if the model trained like described in: https://github.com/FSoft-AI4Code/DocChecker
    # actually achieves the results as described in the paper
    # the model is trained as described in the github readme and should be in a folder called pretrained_model

    # folder DocCheckerReproduction should contain data from: https://drive.google.com/drive/folders/1heqEQGZHgO6gZzCjuQD1EyYertN4SAYZ
    # test1 test2 and test3 are the test sets from summary, returns and param respectively.
    # clean_test_ids.json is the merged  list from the three respective files from the resources folder

    # build_data()
    # make_predicitons()
    # evaluate()




    code_1 = '''

public static boolean isPrime(int n) {
// Checks whether the given integer is prime./n Returns true for primes >= 2, false otherwise.
    if (n < 2) {
        return false;
    }
    if (n % 2 == 0) {
        return n == 2;
    }
    int limit = (int) Math.sqrt(n);
    for (int i = 3; i <= limit; i += 2) {
        if (n % i == 0) {
            return false;
        }
    }
    return true;
}
    '''


    #a =

