#!/usr/bin/env python3
"""Run the controlled API-context example once with a selected feature set."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluation_runner import main as run_evaluation  # noqa: E402


CONSISTENT_COMMIT = "5c8916786d988de8ca7dbc6680685a973810502f"
INCONSISTENT_COMMIT = "2e671ee2e9f193bb4bbfcb5c187e31bacede97a8"
CASE_ROOT = "java/os-hu/contextExampleProject"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--type",
        choices=("none", "context", "all"),
        required=True,
        help="none=no API context/RT; context=API context only; all=context plus round trip",
    )
    parser.add_argument(
        "--config",
        default=str(SCRIPT_DIR / "evaluationConfig.json"),
        help="CASCADE pipeline JSON (default: PaperEvaluation/evaluationConfig.json)",
    )
    parser.add_argument("--cascade-bin", help="CASCADE executable override")
    parser.add_argument("--run-id", help="override the UTC timestamp result-directory name")
    return parser.parse_args()


def method_signature(name: str, returns: str, params: list[str], *modifiers: str) -> dict:
    return {
        "name": name,
        "returns": returns,
        "params": params,
        "modifier": list(modifiers),
        "annotations": [],
        "generics": [],
        "exceptions": [],
    }


def analyzed_case(inclusive: bool) -> list[dict]:
    operator = "<=" if inclusive else "<"
    return [{
        "package": "org.example.subscriptions",
        "doc": (
            "/**\n"
            " * Evaluates a request against a subscription plan.\n"
            " *\n"
            " * @param plan plan that supplies the inclusive unit limit\n"
            " * @param requestedUnits number of units requested\n"
            " * @return an accepted decision when requestedUnits does not exceed the plan limit;\n"
            " *         otherwise a rejected decision\n"
            " */\n"
        ),
        "signature": method_signature(
            "evaluate", "Decision", ["Plan plan", "int requestedUnits"], "public "
        ),
        "language": "Java",
        "parent": {
            "name": "SubscriptionService",
            "doc": "/** Evaluates subscription usage requests. */\n",
            "imports": [],
            "constructors": [],
            "implements": [],
            "extends": [],
            "modifiers": ["public ", "final "],
            "kind": "class",
            "other_methods": [],
            "variables": [],
            "generics": [],
        },
        "code": (
            "{\n"
            f"    return requestedUnits {operator} plan.unitLimit()\n"
            "            ? Decision.accepted()\n"
            "            : Decision.rejected();\n"
            "}"
        ),
        "code_file_path": "src/main/java/org/example/subscriptions/SubscriptionService.java",
        "called_functions": [],
        "test_file_path": "src/test/java/org/example/subscriptions/SubscriptionServiceTest.java",
        "id": 0,
        "junit_version": "4.13.2",
    }]


def write_dataset(path: Path) -> None:
    consistent_id = f"os-hu/contextExampleProject/{CONSISTENT_COMMIT}/1"
    inconsistent_id = f"os-hu/contextExampleProject/{INCONSISTENT_COMMIT}/1"
    files = {
        "dataset_mapping_dict.py": f"mapping = {{{consistent_id!r}: {inconsistent_id!r}}}\n",
        f"{CASE_ROOT}/{CONSISTENT_COMMIT}/1/analyzed.json":
            json.dumps(analyzed_case(inclusive=True), indent=2) + "\n",
        f"{CASE_ROOT}/{CONSISTENT_COMMIT}/1/inconsistency.txt": "False\n",
        f"{CASE_ROOT}/{INCONSISTENT_COMMIT}/1/analyzed.json":
            json.dumps(analyzed_case(inclusive=False), indent=2) + "\n",
        f"{CASE_ROOT}/{INCONSISTENT_COMMIT}/1/inconsistency.txt": "True\n",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="cascade-context-example-") as temporary:
        dataset = Path(temporary) / "context-example.zip"
        write_dataset(dataset)
        forwarded = [
            "--type", args.type,
            "--config", args.config,
            "--dataset", str(dataset),
            "--repo-url-template", "https://github.com/{owner}/{repository}.git",
            "--allow-non-core-dataset",
        ]
        if args.cascade_bin:
            forwarded.extend(("--cascade-bin", args.cascade_bin))
        if args.run_id:
            forwarded.extend(("--run-id", args.run_id))
        return run_evaluation(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
