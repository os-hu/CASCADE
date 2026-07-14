#!/usr/bin/env python3
"""Run the CASCADE core benchmark in an isolated timestamped directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation_report import audit_dataset, load_mapping, mapping_ground_truth, format_duration, write_reports


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SECRET_KEY_PARTS = ("api_key", "apikey", "token", "secret", "password", "credential")


@dataclass(frozen=True)
class Case:
    index: int
    case_id: str
    path: Path
    owner: str
    repository: str
    commit: str
    sample: str

    @property
    def repository_id(self) -> str:
        return f"{self.owner}/{self.repository}"


class Progress:
    def __init__(self, runs_dir: Path, total: int, started_monotonic: float, started_at: str):
        self.total = total
        self.started_monotonic = started_monotonic
        self.started_at = started_at
        self.log_path = runs_dir / "benchmark.log"
        self.progress_path = runs_dir / "progress.json"
        self.statuses: list[dict[str, Any]] = []
        self.current_case: str | None = None
        self.latest_outcome: dict[str, Any] | None = None

    def log(self, message: str) -> None:
        print(message, flush=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
            handle.flush()

    def _counts(self) -> dict[str, int]:
        return {
            "processed": len(self.statuses),
            "scored": sum(status.get("status") == "scored" for status in self.statuses),
            "skipped": sum(status.get("status") == "skipped" for status in self.statuses),
            "errors": sum(status.get("status") == "error" for status in self.statuses),
            "attempted": sum(bool(status.get("attempted")) for status in self.statuses),
        }

    def _eta_seconds(self) -> float | None:
        durations = [
            float(status["duration_seconds"])
            for status in self.statuses
            if status.get("attempted") and status.get("duration_seconds") is not None
        ]
        if not durations:
            return None
        return sum(durations) / len(durations) * max(0, self.total - len(self.statuses))

    def snapshot(self, state: str) -> dict[str, Any]:
        elapsed = time.monotonic() - self.started_monotonic
        eta = self._eta_seconds()
        return {
            "state": state,
            "started_at": self.started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "current_case": self.current_case,
            "total": self.total,
            **self._counts(),
            "elapsed_seconds": elapsed,
            "elapsed": format_duration(elapsed),
            "eta_seconds": eta,
            "eta": format_duration(eta) if eta is not None else None,
            "latest_outcome": self.latest_outcome,
        }

    def write_snapshot(self, state: str) -> None:
        payload = self.snapshot(state)
        temporary = self.progress_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.progress_path)

    def start(self, case: Case) -> float:
        self.current_case = case.case_id
        counts = self._counts()
        percent = case.index / self.total * 100 if self.total else 100.0
        elapsed = format_duration(time.monotonic() - self.started_monotonic)
        eta = self._eta_seconds()
        self.log(f"[{case.index}/{self.total} | {percent:.1f}%] Starting {case.case_id}")
        self.log(
            f"Elapsed: {elapsed} | Completed: {counts['processed']} | Skipped: {counts['skipped']} | "
            f"Errors: {counts['errors']} | ETA: {format_duration(eta) if eta is not None else 'calculating…'}"
        )
        self.write_snapshot("running")
        return time.monotonic()

    def finish(self, case: Case, status: dict[str, Any]) -> None:
        self.statuses.append(status)
        self.latest_outcome = {
            "case_id": case.case_id,
            "status": status["status"],
            "reason": status.get("reason"),
            "prediction": status.get("prediction"),
            "duration_seconds": status.get("duration_seconds"),
        }
        duration = format_duration(status.get("duration_seconds"))
        if status["status"] == "scored":
            verdict = "INCO" if status.get("prediction") else "NoInco"
            self.log(f"[{case.index}/{self.total}] Finished in {duration} — scored: {verdict}")
        elif status["status"] == "skipped":
            self.log(f"[{case.index}/{self.total}] Skipped — {status.get('reason', 'unspecified')}")
        else:
            self.log(f"[{case.index}/{self.total}] Error — {status.get('reason', 'unspecified')}")
        self.current_case = None
        self.write_snapshot("running")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(SCRIPT_DIR / "evaluationConfig.json"), help="CASCADE pipeline JSON")
    parser.add_argument("--dataset", default=str(SCRIPT_DIR / "coreDataset.zip"), help="benchmark ZIP")
    parser.add_argument(
        "--repo-url-template",
        default=os.environ.get("CASCADE_REPO_URL_TEMPLATE", "https://github.com/{owner}/{repository}"),
        help="repository URL template; placeholders: {owner}, {repository}",
    )
    parser.add_argument("--cascade-bin", default=os.environ.get("CASCADE_BIN"), help="CASCADE executable override")
    parser.add_argument("--run-id", help="override the UTC timestamp directory name")
    parser.add_argument("--allow-non-core-dataset", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Evaluation config not found: {path}")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Evaluation config is not valid JSON: {error}") from error
    required = ("Extraction", "CodeGenerator", "TestGenerator", "Analysis", "Executor")
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Evaluation config is missing: {', '.join(missing)}")
    if config.get("Analysis", {}).get("name") != "DatasetAnalysis":
        raise ValueError("Core evaluation requires Analysis.name to be DatasetAnalysis")
    if config.get("Executor", {}).get("name") != "MavenJavaExecutor":
        raise ValueError("Core evaluation requires Executor.name to be MavenJavaExecutor")
    return config


def redact(value: Any, key: str = "") -> Any:
    if any(part in key.lower() for part in SECRET_KEY_PARTS):
        return "<redacted>"
    if isinstance(value, dict):
        return {item_key: redact(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def model_name(config: dict[str, Any]) -> str:
    test_model = config.get("TestGenerator", {}).get("kwargs", {}).get("model")
    code_model = config.get("CodeGenerator", {}).get("kwargs", {}).get("model")
    if test_model and code_model and test_model != code_model:
        return f"tests={test_model}; code={code_model}"
    return str(test_model or code_model or "unspecified")


def resolve_cascade_binary(override: str | None) -> str:
    candidates = [
        override,
        str(SCRIPT_DIR / "venv-cascade" / "bin" / "CASCADE"),
        str(REPO_ROOT / "cascade.venv" / "bin" / "CASCADE"),
        shutil.which("CASCADE"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    raise ValueError("CASCADE executable not found; set CASCADE_BIN or prepare PaperEvaluation/venv-cascade")


def create_run_root(run_id: str | None) -> tuple[str, Path]:
    base_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = SCRIPT_DIR / "evalRuns" / base_id
    if root.exists():
        suffix = 1
        while (SCRIPT_DIR / "evalRuns" / f"{base_id}-{suffix}").exists():
            suffix += 1
        root = SCRIPT_DIR / "evalRuns" / f"{base_id}-{suffix}"
    root.mkdir(parents=True)
    (root / "runs").mkdir()
    (root / "results").mkdir()
    return root.name, root


def safe_extract(archive: Path, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if destination_resolved not in target.parents and target != destination_resolved:
                raise ValueError(f"Unsafe ZIP member: {member.filename}")
        bundle.extractall(destination)


def discover_cases(java_root: Path) -> list[Case]:
    paths = sorted(java_root.glob("*/*/*/*/analyzed.json"), key=lambda path: path.parent.relative_to(java_root).as_posix())
    cases = []
    for index, analyzed in enumerate(paths, start=1):
        relative = analyzed.parent.relative_to(java_root)
        if len(relative.parts) != 4:
            continue
        owner, repository, commit, sample = relative.parts
        cases.append(Case(index, relative.as_posix(), analyzed.parent, owner, repository, commit, sample))
    return cases


def run_logged(command: list[str], log_path: Path, cwd: Path | None = None, stdin_path: Path | None = None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"$ {' '.join(command)}\n")
        log_handle.flush()
        stdin_handle = stdin_path.open("rb") if stdin_path else None
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                stdin=stdin_handle,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                check=False,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            log_handle.write(f"[exit {completed.returncode}]\n")
            return completed.returncode
        except OSError as error:
            log_handle.write(f"[execution error] {error}\n")
            return 127
        finally:
            if stdin_handle:
                stdin_handle.close()


def copy_case_artifacts(output_dir: Path, case_dir: Path) -> None:
    names = {
        "result.txt": "result_CASCADE.txt",
        "log.txt": "log_CASCADE.txt",
        "errors.txt": "errors_CASCADE.txt",
        "analyzed.json": "analyzed.json",
    }
    for source_name, destination_name in names.items():
        source = output_dir / source_name
        if source.exists():
            shutil.copy2(source, case_dir / destination_name)
    for name in ("log_CASCADE.txt", "errors_CASCADE.txt"):
        path = case_dir / name
        if not path.exists():
            path.touch()


def read_case_payload(case: Case) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    analyzed_path = case.path / "analyzed.json"
    try:
        payload = json.loads(analyzed_path.read_text(encoding="utf-8"))
        context = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(context, dict):
            return [], None
    except (OSError, json.JSONDecodeError):
        return [], None
    events = context.get("compiler_events") or []
    model_payload = {
        "case_id": case.case_id,
        "new_tests": context.get("new_tests"),
        "new_tests_history": context.get("new_tests_history"),
        "repair_history": context.get("repair_history"),
        "new_code": context.get("new_code"),
        "new_code_response": context.get("new_code_response"),
    }
    if not any(value is not None and value != [] for key, value in model_payload.items() if key != "case_id"):
        model_payload = None
    return events, model_payload


def classify_result(path: Path) -> tuple[bool | None, str | None, str | None]:
    if not path.is_file():
        return None, None, "CASCADE did not produce result.txt"
    result = path.read_text(encoding="utf-8", errors="replace").strip()
    normalized = result.replace("\n", " ")
    if "; error;" in normalized or normalized.startswith("Error during analysis"):
        return None, result, "CASCADE reported an analysis/compiler error"
    if normalized.startswith("INCO"):
        return True, result, None
    if normalized.startswith("NoInco"):
        return False, result, None
    return None, result, "CASCADE produced an unrecognized result"


def status_base(case: Case, truth: bool, duration: float) -> dict[str, Any]:
    return {
        "index": case.index,
        "case_id": case.case_id,
        "repository": case.repository_id,
        "commit": case.commit,
        "sample": case.sample,
        "ground_truth": truth,
        "duration_seconds": duration,
    }


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()


def git_revision() -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config_path = Path(args.config).expanduser().resolve()
    dataset_path = Path(args.dataset).expanduser().resolve()
    if not dataset_path.is_file():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 2
    try:
        config = load_and_validate_config(config_path)
        cascade_binary = resolve_cascade_binary(args.cascade_bin)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    run_id, run_root = create_run_root(args.run_id)
    runs_dir = run_root / "runs"
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    config_bytes = config_path.read_bytes()
    manifest = {
        "run_id": run_id,
        "state": "preparing",
        "started_at": started_at,
        "dataset": str(dataset_path),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "config": redact(config),
        "model": model_name(config),
        "cascade_binary": cascade_binary,
        "cascade_git_revision": git_revision(),
        "repo_url_template": args.repo_url_template,
    }
    manifest_path = runs_dir / "run_manifest.json"
    write_manifest(manifest_path, manifest)

    interrupted = False
    progress: Progress | None = None
    mapping: dict[str, str] = {}
    audit: dict[str, Any] = {"case_count": 0, "mapping_pairs": 0, "archive_labels": {}, "label_mismatches": []}
    work_dir = runs_dir / "_work"
    try:
        safe_extract(dataset_path, runs_dir)
        java_root = runs_dir / "java"
        mapping_path = runs_dir / "dataset_mapping_dict.py"
        mapping = load_mapping(mapping_path)
        audit = audit_dataset(java_root, mapping)
        cases = discover_cases(java_root)
        if not args.allow_non_core_dataset:
            problems = []
            if len(cases) != 142:
                problems.append(f"expected 142 cases, found {len(cases)}")
            if len(mapping) != 71:
                problems.append(f"expected 71 mapping pairs, found {len(mapping)}")
            if audit["unmapped_cases"] or audit["missing_mapped_cases"]:
                problems.append("mapping does not cover the dataset exactly")
            if problems:
                raise ValueError("Core dataset validation failed: " + "; ".join(problems))

        truth = mapping_ground_truth(mapping)
        progress = Progress(runs_dir, len(cases), started, started_at)
        progress.write_snapshot("preparing")
        manifest.update({"state": "running", "dataset_audit": audit, "case_count": len(cases)})
        write_manifest(manifest_path, manifest)
        progress.log(f"Run directory: {run_root}")
        progress.log(f"Core dataset: {len(cases)} cases; {len(mapping)} mapped pairs; model: {model_name(config)}")
        if audit["label_mismatches"]:
            progress.log(f"Dataset audit: {len(audit['label_mismatches'])} archive label mismatch(es); mapping labels will be used")

        repo_cache: dict[str, tuple[Path | None, str | None]] = {}
        commit_cache: dict[tuple[str, str], tuple[Path | None, str | None]] = {}
        status_path = runs_dir / "case_status.jsonl"
        model_output_path = runs_dir / "model_outputs.jsonl"
        setup_logs = runs_dir / "setup_logs"
        work_dir.mkdir(parents=True, exist_ok=True)

        for case in cases:
            case_started = progress.start(case)
            repo_key = case.repository_id
            if repo_key not in repo_cache:
                clone_path = work_dir / "clones" / f"{case.owner}__{case.repository}"
                clone_path.parent.mkdir(parents=True, exist_ok=True)
                url = args.repo_url_template.format(owner=case.owner, repository=case.repository)
                clone_code = run_logged(
                    ["git", "clone", "--quiet", url, str(clone_path)],
                    setup_logs / f"{case.owner}__{case.repository}__clone.log",
                )
                repo_cache[repo_key] = (clone_path, None) if clone_code == 0 else (None, "repository unavailable")

            clone_path, repo_error = repo_cache[repo_key]
            if repo_error:
                duration = time.monotonic() - case_started
                status = {
                    **status_base(case, truth[case.case_id], duration),
                    "status": "skipped", "reason": repo_error, "attempted": False,
                    "prediction": None, "result": None, "compiler_events": [],
                }
                append_jsonl(status_path, status)
                progress.finish(case, status)
                continue

            commit_key = (repo_key, case.commit)
            if commit_key not in commit_cache:
                commit_log = setup_logs / f"{case.owner}__{case.repository}__{case.commit}__prepare.log"
                checkout_code = run_logged(["git", "checkout", "--quiet", "--force", case.commit], commit_log, cwd=clone_path)
                if checkout_code != 0:
                    commit_cache[commit_key] = (None, "commit unavailable")
                else:
                    template = work_dir / "commits" / f"{case.owner}__{case.repository}__{case.commit}"
                    if template.exists():
                        shutil.rmtree(template)
                    shutil.copytree(clone_path, template, ignore=shutil.ignore_patterns(".git"))
                    patch_path = case.path.parent / "file.patch"
                    if patch_path.is_file():
                        patch_code = run_logged(["patch", "-p1", "-f"], commit_log, cwd=template, stdin_path=patch_path)
                        if patch_code != 0:
                            shutil.rmtree(template, ignore_errors=True)
                            commit_cache[commit_key] = (None, "dataset patch failed")
                        else:
                            commit_cache[commit_key] = (template, None)
                    else:
                        commit_cache[commit_key] = (template, None)

            template, commit_error = commit_cache[commit_key]
            if commit_error:
                duration = time.monotonic() - case_started
                status = {
                    **status_base(case, truth[case.case_id], duration),
                    "status": "skipped", "reason": commit_error, "attempted": False,
                    "prediction": None, "result": None, "compiler_events": [],
                }
                append_jsonl(status_path, status)
                progress.finish(case, status)
                continue

            output_dir = case.path / "CASCADE"
            repository_dir = output_dir / "repository"
            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.mkdir()
            shutil.copytree(template, repository_dir)
            shutil.copy2(case.path / "analyzed.json", output_dir / "analyzed.json")
            console_log = case.path / "console_CASCADE.log"
            exit_code = run_logged(
                [
                    cascade_binary, "run", "-i", str(repository_dir), "-o", str(output_dir),
                    "-c", str(config_path), "-ana", "debug:3",
                ],
                console_log,
                cwd=output_dir,
            )
            shutil.rmtree(repository_dir, ignore_errors=True)
            copy_case_artifacts(output_dir, case.path)
            prediction, result, result_error = classify_result(case.path / "result_CASCADE.txt")
            events, output_payload = read_case_payload(case)
            if output_payload:
                append_jsonl(model_output_path, output_payload)

            duration = time.monotonic() - case_started
            if result_error:
                reason = result_error if exit_code == 0 else f"CASCADE exited {exit_code}; {result_error}"
                status_kind = "error"
            else:
                reason = None if exit_code == 0 else f"CASCADE exited {exit_code} but produced a valid result"
                status_kind = "scored"
            status = {
                **status_base(case, truth[case.case_id], duration),
                "status": status_kind,
                "reason": reason,
                "attempted": True,
                "prediction": prediction,
                "result": result,
                "cascade_exit_code": exit_code,
                "compiler_events": events,
            }
            append_jsonl(status_path, status)
            progress.finish(case, status)

    except KeyboardInterrupt:
        interrupted = True
        if progress:
            progress.log("Interrupted by user; writing partial reports")
    except Exception as error:
        interrupted = True
        if progress:
            progress.log(f"Fatal runner error: {error}")
        else:
            print(f"Fatal runner error: {error}", file=sys.stderr)
        manifest["fatal_error"] = str(error)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        duration = time.monotonic() - started
        statuses = progress.statuses if progress else []
        if mapping and audit.get("case_count"):
            try:
                write_reports(
                    run_root, statuses, mapping, audit, model_name(config), run_id, duration, interrupted=interrupted
                )
            except Exception as report_error:
                interrupted = True
                manifest["report_error"] = str(report_error)
                if progress:
                    progress.log(f"Report generation failed: {report_error}")
        manifest.update({
            "state": "interrupted" if interrupted else "complete",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration,
            "processed_cases": len(statuses),
        })
        write_manifest(manifest_path, manifest)
        if progress:
            progress.current_case = None
            progress.write_snapshot("interrupted" if interrupted else "complete")
            counts = progress._counts()
            progress.log(
                f"Final: {counts['processed']}/{progress.total} processed — scored {counts['scored']}, "
                f"skipped {counts['skipped']}, errors {counts['errors']}, runtime {format_duration(duration)}"
            )
            progress.log(f"Results: {run_root / 'results'}")

    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
