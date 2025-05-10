import ast
import sys
import os


def compute_metrics(counts):
    TP = counts['TP']
    FP = counts['FP']
    FN = counts['FN']
    TN = counts['TN']
    prec = TP / (TP + FP) if (TP + FP) > 0 else 0
    rec = TP / (TP + FN) if (TP + FN) > 0 else 0
    spec = TN / (TN + FP) if (TN + FP) > 0 else 0
    acc = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0
    return {
        "TP": TP,
        "FP": FP,
        "TN": TN,
        "FN": FN,
        "Prec": f"{prec:.4f}",
        "Rec": f"{rec:.4f}",
        "F1": f"{f1:.4f}",
        "Spec": f"{spec:.4f}",
        "acc": f"{acc:.4f}"
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
    result = {
        "phase2" : "",
        "phase1" : ""
    }

    if "Positive" in pd:
        result["phase2"] = "TP" if gt else "FP"
    else:
        result["phase2"] = "FN" if gt else "TN"

    # here just getting into phase 2 already means we have predicted a positive
    prediction = "Positive" if "step 2" in pd else "Negative"
    if prediction == "Positive":
        result["phase1"] = "TP" if gt else "FP"
    else:
        result["phase1"] = "FN" if gt else "TN"

    return result


def eval_baseline(gt, pd):
    pass


def eval_docchecker(gt, pd):
    pass


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
        gt = get_groundtruth(result_path)
        pd = get_prediction(result_path)
        eval_results = eval(gt, pd)

        for version, result in eval_results.items():
            if version not in counts:
                counts[version] = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
            counts[version][result] += 1

    return counts

def print_report(driver_name, results, to_file=False):
    print(driver_name)
    for phase, metrics in results.items():
        print(f"   {phase}: {str(metrics)}")
    print()

if __name__ == '__main__':
    mapping = {"c": "CASCADE", "b": "Baseline", "d": "DocChecker", "j": "JDoctor"}
    if len(sys.argv) != 2:
        sys.exit("Usage: python main.py <letters>")
    try:
        drivers = [mapping[ch.lower()] for ch in sys.argv[1]]
    except KeyError as bad:
        sys.exit(f"Unknown letter code: {bad.args[0]!r}")

    for driver in drivers:
        versions = evaluate_driver(driver)

        results = {}
        for version, counts in versions.items():
            metrics = compute_metrics(counts)
            results[version] = metrics

        print_report(driver, results)







