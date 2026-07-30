import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import textwrap
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from cascade.utils.JavaUtils import build_api_context
from evaluation_report import (
    _latex_artifacts, aggregate_run_metrics, audit_dataset, build_metrics, latex_escape, load_mapping,
)
from evaluation_runner import Case, Progress, configure_for_type, parse_args


class ReportTests(unittest.TestCase):
    def test_compiler_metrics_track_attempts_and_resolution(self):
        statuses = [
            {
                "case_id": "fix", "status": "scored", "ground_truth": False, "prediction": False,
                "attempted": True, "duration_seconds": 2,
                "compiler_events": [{"phase": "phase1_initial", "had_compiler_error": False}],
            },
            {
                "case_id": "inco", "status": "scored", "ground_truth": True, "prediction": True,
                "attempted": True, "duration_seconds": 4,
                "compiler_events": [
                    {"phase": "phase1_initial", "had_compiler_error": True},
                    {"phase": "phase1_repair", "repair_attempt": 1, "had_compiler_error": True},
                    {"phase": "phase1_repair", "repair_attempt": 2, "had_compiler_error": False,
                     "test_source_present": True, "test_results": [1, 0, 0]},
                    {"phase": "phase2", "had_compiler_error": True},
                ],
            },
        ]
        metrics = build_metrics(statuses, 2, {"fix": "inco"}, 6)
        self.assertEqual(metrics["classification"]["f1"], 1.0)
        compiler = metrics["compiler"]
        self.assertEqual(compiler["phase1_initial_failures"], 1)
        self.assertEqual(compiler["phase2_failures"], 1)
        self.assertEqual(compiler["compiler_failing_attempts"], 3)
        self.assertEqual(compiler["repairs_resolved"], 1)
        self.assertEqual(compiler["resolved_after_2"], 1)
        self.assertEqual(compiler["mean_repair_attempts"], 2)

    def test_empty_compiler_success_is_not_a_usable_repair(self):
        statuses = [{
            "case_id": "inco", "status": "error", "ground_truth": True, "prediction": None,
            "attempted": True, "duration_seconds": 1,
            "compiler_events": [
                {"phase": "phase1_initial", "had_compiler_error": True, "test_results": [0, 0, 0]},
                {"phase": "phase1_repair", "repair_attempt": 1, "had_compiler_error": False,
                 "test_source_present": False, "test_results": [0, 0, 0]},
            ],
        }]
        compiler = build_metrics(statuses, 1, {"fix": "inco"}, 1)["compiler"]
        self.assertEqual(compiler["repairs_resolved"], 0)
        self.assertEqual(compiler["repairs_unresolved"], 1)
        self.assertEqual(compiler["compile_only_resolutions"], 1)

    def test_aggregate_uses_per_run_arithmetic_means(self):
        base = [{
            "case_id": "fix", "status": "scored", "ground_truth": False, "prediction": False,
            "attempted": True, "duration_seconds": 1, "compiler_events": [],
            "result": "NoInco; pass; step 1",
        }]
        first = {"run_id": "one", "model": "m", **build_metrics(base, 1, {"fix": "inco"}, 10)}
        second_status = [{**base[0], "status": "error", "prediction": None, "result": "NoInco; error; step 1"}]
        second = {"run_id": "two", "model": "m", **build_metrics(second_status, 1, {"fix": "inco"}, 20)}
        aggregate = aggregate_run_metrics([first, second])
        self.assertEqual(aggregate["summary"]["valid_verdicts"]["mean"], 0.5)
        self.assertEqual(aggregate["summary"]["correct"]["mean"], 0.5)
        self.assertEqual(aggregate["summary"]["runtime_seconds"]["mean"], 15)

    def test_type_modes_are_explicit_and_runs_must_be_positive(self):
        config = {"TestGenerator": {"name": "custom", "kwargs": {"model": "m"}}}
        self.assertEqual(configure_for_type(config, "none")["TestGenerator"]["name"], "MultiStepJavaTestGenerator")
        self.assertEqual(configure_for_type(config, "context")["TestGenerator"]["name"], "MultiStepJavaTestGenerator")
        all_config = configure_for_type(config, "all")
        self.assertEqual(all_config["TestGenerator"]["name"], "RoundTripJavaTestGenerator")
        self.assertEqual(all_config["TestGenerator"]["kwargs"]["max_roundtrips"], 2)
        with self.assertRaises(SystemExit):
            parse_args(["--type", "all", "--runs", "0"])

    def test_zero_denominators_and_latex_are_stable(self):
        metrics = build_metrics([], 142, {"fix": "inco"}, 0)
        values, header, row, table = _latex_artifacts("run_1", "model&name", metrics)
        self.assertIn("run\\_1", row)
        self.assertIn("model\\&name", row)
        self.assertIn("0/0", row)
        self.assertEqual(len(header.split("&")), 13)
        self.assertIn("\\begin{tabular}{llrrrrrrrrrrr}", table)
        self.assertEqual(values["expected"], 142)
        self.assertEqual(latex_escape("a_b%"), r"a\_b\%")

    def test_api_context_uses_constructor_signatures_and_keeps_target_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            extracted = [
                {"package": f"a.package{i:02d}", "parent": {"name": f"Type{i}"},
                 "signature": {"name": "method", "modifier": []}}
                for i in range(30)
            ]
            extracted.append({"package": "z.target", "parent": {"name": "Target"},
                              "signature": {"name": "method", "modifier": []}})
            (root / "extracted.json").write_text(json.dumps(extracted), encoding="utf-8")
            context = {
                "package": "z.target",
                "signature": {"returns": "void", "params": []},
                "parent": {
                    "name": "Target", "kind": "class", "modifiers": [],
                    "constructors": ["public Target() { secretImplementation(); }"],
                    "other_methods": [],
                },
            }
            block = build_api_context(context, str(root), max_packages=3)
            self.assertIn("public Target()", block)
            self.assertNotIn("secretImplementation", block)
            self.assertIn("Known project packages include: z.target", block)
            self.assertNotIn("This project only provides", block)

    def test_real_core_archive_mapping_audit(self):
        archive = HERE / "coreDataset.zip"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(root)
            mapping = load_mapping(root / "dataset_mapping_dict.py")
            audit = audit_dataset(root / "java", mapping)
        self.assertEqual(audit["case_count"], 142)
        self.assertEqual(audit["mapping_pairs"], 71)
        self.assertEqual(len(audit["label_mismatches"]), 1)
        self.assertTrue(audit["label_mismatches"][0]["case_id"].startswith("apache/commons-codec/6175c99"))


class ProgressTests(unittest.TestCase):
    def test_progress_advances_across_skips_and_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            progress = Progress(runs, 2, time.monotonic(), "2026-01-01T00:00:00+00:00")
            first = Case(1, "o/r/c/1", runs, "o", "r", "c", "1")
            second = Case(2, "o/r/c/2", runs, "o", "r", "c", "2")
            progress.start(first)
            progress.finish(first, {"status": "skipped", "reason": "repository unavailable", "attempted": False, "duration_seconds": 0})
            progress.start(second)
            progress.finish(second, {"status": "error", "reason": "bad result", "attempted": True, "duration_seconds": 1})
            snapshot = json.loads((runs / "progress.json").read_text())
            self.assertEqual(snapshot["processed"], 2)
            self.assertEqual(snapshot["skipped"], 1)
            self.assertEqual(snapshot["errors"], 1)
            log = (runs / "benchmark.log").read_text()
            self.assertIn("[1/2 | 50.0%]", log)
            self.assertIn("[2/2 | 100.0%]", log)
            self.assertIn("Skipped — repository unavailable", log)
            self.assertIn("Error — bad result", log)


class FakeRunIntegrationTest(unittest.TestCase):
    def test_runner_writes_progress_metrics_model_output_and_latex(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source_repo = temp_path / "repos" / "owner" / "project"
            source_repo.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet", str(source_repo)], check=True)
            subprocess.run(["git", "-C", str(source_repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(source_repo), "config", "user.name", "Test"], check=True)
            (source_repo / "pom.xml").write_text("<project/>\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source_repo), "add", "pom.xml"], check=True)
            subprocess.run(["git", "-C", str(source_repo), "commit", "--quiet", "-m", "fixture"], check=True)
            commit = subprocess.check_output(["git", "-C", str(source_repo), "rev-parse", "HEAD"], text=True).strip()

            dataset_tree = temp_path / "dataset"
            for sample, label in (("fix", "False"), ("inco", "True")):
                case = dataset_tree / "java" / "owner" / "project" / commit / sample
                case.mkdir(parents=True)
                (case / "analyzed.json").write_text("[{}]\n", encoding="utf-8")
                (case / "inconsistency.txt").write_text(label, encoding="utf-8")
            (dataset_tree / "dataset_mapping_dict.py").write_text(
                f"mapping = {{'owner/project/{commit}/fix': 'owner/project/{commit}/inco'}}\n", encoding="utf-8"
            )
            archive = temp_path / "fixture.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for path in dataset_tree.rglob("*"):
                    if path.is_file():
                        bundle.write(path, path.relative_to(dataset_tree))

            config = temp_path / "evaluationConfig.json"
            config.write_text(json.dumps({
                "Extraction": {"name": "JavaExtraction", "kwargs": {}},
                "CodeGenerator": {"name": "JavaCodeGenerator", "kwargs": {"model": "fake_model"}},
                "TestGenerator": {"name": "MultiStepJavaTestGenerator", "kwargs": {"model": "fake_model"}},
                "Analysis": {"name": "DatasetAnalysis", "kwargs": {}},
                "Executor": {"name": "MavenJavaExecutor", "kwargs": {}},
            }), encoding="utf-8")

            fake = temp_path / "fake-cascade"
            fake.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json, pathlib, sys
                out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])
                sample = out.parent.name
                prediction = 'INCO' if sample == 'inco' else 'NoInco'
                events = [{'phase': 'phase1_initial', 'repair_attempt': None,
                           'had_compiler_error': sample == 'inco', 'compiler_errors': 'fake error' if sample == 'inco' else None,
                           'compiler_error_matches': [], 'test_results': [1, 0, 0]}]
                (out / 'result.txt').write_text(prediction + '; pass; step 1; ; ; ; og tests exist; 0')
                (out / 'log.txt').write_text('fake log')
                (out / 'errors.txt').write_text('')
                (out / 'analyzed.json').write_text(json.dumps([{'compiler_events': events,
                    'new_tests_history': [{'response': 'complete model output'}]}]))
                """), encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            run_id = f"test-{os.getpid()}"
            run_root = HERE / "evalRuns" / run_id
            try:
                command = [
                    sys.executable, str(HERE / "evaluation_runner.py"),
                    "--config", str(config), "--type", "none", "--dataset", str(archive),
                    "--cascade-bin", str(fake), "--allow-non-core-dataset", "--run-id", run_id,
                    "--repo-url-template", str(temp_path / "repos" / "{owner}" / "{repository}"),
                ]
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertIn("[1/2 | 50.0%] Starting", completed.stdout)
                self.assertIn("Final: 2/2 processed", completed.stdout)
                progress = json.loads((run_root / "runs" / "progress.json").read_text())
                self.assertEqual(progress["state"], "complete")
                self.assertEqual(progress["processed"], 2)
                metrics = json.loads((run_root / "results" / "metrics.json").read_text())
                self.assertEqual(metrics["classification"]["f1"], 1.0)
                self.assertEqual(metrics["compiler"]["phase1_initial_failures"], 1)
                self.assertTrue((run_root / "results" / "table_row.tex").is_file())
                if shutil.which("pdflatex"):
                    latex = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "table.tex"],
                                           cwd=run_root / "results", capture_output=True, text=True, check=False)
                    self.assertEqual(latex.returncode, 0, latex.stdout + latex.stderr)
                self.assertIn("complete model output", (run_root / "runs" / "model_outputs.jsonl").read_text())

                multi_id = f"{run_id}-multi"
                multi_root = HERE / "evalRuns" / multi_id
                multi_command = [*command, "--run-id", multi_id, "--runs", "2"]
                multi = subprocess.run(multi_command, capture_output=True, text=True, check=False)
                self.assertEqual(multi.returncode, 0, multi.stdout + multi.stderr)
                self.assertTrue((multi_root / "replicates" / "run-001" / "results" / "metrics.json").is_file())
                self.assertTrue((multi_root / "replicates" / "run-002" / "results" / "metrics.json").is_file())
                aggregate = json.loads((multi_root / "results" / "metrics.json").read_text())
                self.assertEqual(aggregate["run_count"], 2)
                self.assertEqual(aggregate["summary"]["valid_verdicts"]["mean"], 2)
                self.assertTrue((multi_root / "results" / "table.tex").is_file())
            finally:
                shutil.rmtree(run_root, ignore_errors=True)
                shutil.rmtree(HERE / "evalRuns" / f"{run_id}-multi", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()