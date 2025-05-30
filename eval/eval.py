import ast
import sys
import os
import re

def compute_metrics(counts, mapping):
    always_positive = 0
    always_negative = 0

    self_consistent_correct = 0

    for fix, inco in mapping.items():
        if inco in counts["TP"] and fix in counts["TN"]:
            self_consistent_correct += 1

        if inco in counts["TP"] and fix in counts["FP"]:
            always_positive += 1
        if fix in counts["TN"] and inco in counts["FN"]:
            always_negative += 1


    TP = len(counts['TP'])
    FP = len(counts['FP'])
    FN = len(counts['FN'])
    TN = len(counts['TN'])
    prec = TP / (TP + FP) if (TP + FP) > 0 else 0
    rec = TP / (TP + FN) if (TP + FN) > 0 else 0
    spec = TN / (TN + FP) if (TN + FP) > 0 else 0
    acc = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0
    documentation_invariant = (always_positive + always_negative) / len(mapping)
    scc = self_consistent_correct / TP if TP > 0 else 0
    wins = self_consistent_correct / len(mapping) if len(mapping) > 0 else 0

    return {
        "TP": TP,
        "FP": FP,
        "TN": TN,
        "FN": FN,
        "Prec": f"{prec:.3f}",
        "Rec": f"{rec:.3f}",
        "F1": f"{f1:.3f}",
        "Spec": f"{spec:.3f}",
        "acc": f"{acc:.3f}",
        "documentation_invariant": f"{documentation_invariant:.3f}",
        "always_positive": always_positive,
        "always_negative": always_negative,
        "self_consistent_correct": self_consistent_correct,
        "scc_rate": f"{scc:.3f}",
        "wins": f"{wins:.3f}"
    }

def walk_directory(target, root='./java/'):
    """
    Walks through the directory tree under `root` and yields paths to files named `target_file`.
    possible targets: CASCADE, DocChecker, JDoctor, Baseline
    """
    target_file = 'result_' + target + ".txt"
    for dirpath, _, filenames in os.walk(root):
        if target_file in filenames:
            yield os.path.join(dirpath, target_file)


def get_groundtruth(file_path):
    id_path = os.path.dirname(file_path)
    ground_truth_file = os.path.join(id_path, "inconsistency.txt")
    with open(ground_truth_file, 'r') as f2:
        content2 = f2.read()
        gt = ast.literal_eval(content2)
    return gt


def get_prediction(file_path):
    with open(file_path, 'r') as f:
        prediction = f.read().strip()
    return prediction



def eval_cascade(gt, pd):
    """Returns a dict with the specific results (TP TN etc.) for each version  (phase 1  and phase 2)"""
    # results look like this:

    results = {
    }

    # here just getting into phase 2 already means we have predicted a positive
    prediction = "Positive" if "step 2" in pd else "Negative"
    if prediction == "Positive":
        results["Justphase1"] = "TP" if gt else "FP"
    else:
        results["Justphase1"] = "FN" if gt else "TN"

    if "INCO" in pd:
        results["phase2"] = "TP" if gt else "FP"
    else:
        results["phase2"] = "FN" if gt else "TN"


    # parse the result string which looks like this: NoInco; fail; step 2 (C'+T'); (9, 1, 0); (9, 1, 0); p2p: 9, f2f: 1, p2f: 0, f2p: 0; og tests exist; 1
    parts = [p.strip() for p in pd.split(";")]

    num_repair_steps = parts[-1]

    segment = parts[5] if len(parts) > 5 else ""
    if not segment:
        info = {"p2p": 0, "f2f": 0, "p2f": 0, "f2p": 0}
    else:
        # turn  p2p: 9, f2f: 1, …   into   "p2p": 9, "f2f": 1, …
        quoted = re.sub(r"(\w+)\s*:", r'"\1":', segment)
        info = ast.literal_eval("{" + quoted + "}")

    if info["f2p"] > 0:
        results["f2p>0"] = "TP" if gt else "FP"
    else:
        results["f2p>0"] = "FN" if gt else "TN"

    if info["f2p"] > info["p2f"]:
        results["f2p>p2f"] = "TP" if gt else "FP"
    else:
        results["f2p>p2f"] = "FN" if gt else "TN"

    if info["f2p"] > 0  and info["p2f"] == 0:
        results["nop2f"] = "TP" if gt else "FP"
    else:
        results["nop2f"] = "FN" if gt else "TN"

    return results


def eval_baseline(gt, pd):
    # results look like this:     e.g. Negative; Negative; Positive; Negative;    labels simple-Consistent; simple-Inconsistent; complex-Consistent; complex-Inconsistent
    split_predictions = pd.replace(" ", "").split(";")
    labels = ["simpleConsistent", "simpleInconsistent", "complexConsistent", "complexInconsistent"]
    results = {}

    for i in range(4):
        if split_predictions[i] == "Positive":
            results[labels[i]] = "TP" if gt else "FP"
        else:
            results[labels[i]] = "FN" if gt else "TN"

    more_labels = ["atLeast1", "atLeast2", "atLeast3", "all4"]
    num_of_positives = split_predictions.count("Positive")

    for i in range(4):
        if num_of_positives >= i + 1:
            results[more_labels[i]] = "TP" if gt else "FP"
        else:
            results[more_labels[i]] = "FN" if gt else "TN"

    return results


def eval_docchecker(gt, pd):
    # results look like this:     Error; Negative; Positive; [Negative,Positive,Negative]       asCodeis, oneLine, singleLines, whole results
    split_predictions = pd.replace(" ", "").split(";")
    labels = ["asCodeis", "oneLine", "singleLines"]
    results = {}

    for i in range(3):
        if split_predictions[i] == "Positive":
            results[labels[i]] = "TP" if gt else "FP"
        else:
            results[labels[i]] = "FN" if gt else "TN"

    return results


def eval_jdoctor(gt, pd):
    pass



def evaluate_driver(driver):
    """Returns dict counts[version][label].  containting the tp etc. for each version that the specific driver has/ or is evalutated on"""
    if driver == "CASCADE":
        eval = eval_cascade
    elif driver == "Baseline":
        eval = eval_baseline
    elif driver == "DocChecker":
        eval = eval_docchecker
    elif driver == "JDoctor":
        eval = eval_jdoctor
    else:
        return

    counts = {}
    for result_path in walk_directory(driver):
        # get qualitiatve id
        id = os.path.dirname(result_path).replace("./java/", "")

        gt = get_groundtruth(result_path)
        pd = get_prediction(result_path)
        eval_results = eval(gt, pd)

        for version, result in eval_results.items():
            if version not in counts:
                counts[version] = {"TP": [], "FP": [], "FN": [], "TN": []}

            counts[version][result].append(id)

    return counts

def print_report(driver_name, results, to_file=False):
    print(driver_name)
    for phase, metrics in results.items():
        print(f"   {phase}: {str(metrics)}")
    print()

if __name__ == '__main__':
    from dataset_mapping_dict import mapping
    # read in pairs of consistent/inconsistent pairs

    driver_abbreviations = {"c": "CASCADE", "b": "Baseline", "d": "DocChecker", "j": "JDoctor"}
    # Need at least one letter after the script name
    if len(sys.argv) < 2:
        sys.exit("Usage: python eval.py <letter> [<letter> ...]")

    drivers = []
    for arg in sys.argv[1:]:  # every extra CLI token, not one long string
        try:
            drivers.append(driver_abbreviations[arg.lower()])
        except KeyError:
            sys.exit(f"Unknown letter code: {arg!r}")



    for driver in drivers:
        versions = evaluate_driver(driver)

        results = {}
        for version, counts in versions.items():
            metrics = compute_metrics(counts, mapping)
            results[version] = metrics

        print_report(driver, results)







