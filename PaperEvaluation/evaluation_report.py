#!/usr/bin/env python3
"""Normalize CASCADE benchmark artifacts and render human/machine reports."""

from __future__ import annotations

import ast
import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


CLASSIFICATION_FIELDS = ("precision", "recall", "f1", "specificity", "accuracy", "balanced_accuracy")


def safe_div(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def format_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return "--"
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def format_score(value: float | None) -> str:
    return "--" if value is None else f"{value:.3f}"


def format_percentage(value: float | None) -> str:
    return "--" if value is None else f"{value * 100:.1f}%"


def format_rate(count: int, denominator: int) -> str:
    rate = safe_div(count, denominator)
    if rate is None:
        return f"{count}/{denominator} (--)"
    return f"{count}/{denominator} ({rate * 100:.1f}\\%)"


def load_mapping(mapping_path: Path) -> dict[str, str]:
    tree = ast.parse(mapping_path.read_text(encoding="utf-8"), filename=str(mapping_path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "mapping" for target in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                break
            return {str(key): str(item) for key, item in value.items()}
    raise ValueError(f"Could not find a literal mapping dictionary in {mapping_path}")


def audit_dataset(java_root: Path, mapping: dict[str, str]) -> dict[str, Any]:
    label_files = sorted(java_root.glob("*/*/*/*/inconsistency.txt"))
    labels = {
        path.parent.relative_to(java_root).as_posix(): path.read_text(encoding="utf-8").strip()
        for path in label_files
    }
    mapped_ids = set(mapping) | set(mapping.values())
    mismatches = []
    for case_id, expected in [(key, "False") for key in mapping] + [(value, "True") for value in mapping.values()]:
        actual = labels.get(case_id)
        if actual != expected:
            mismatches.append({"case_id": case_id, "archive_label": actual, "mapping_label": expected})

    return {
        "case_count": len(labels),
        "mapping_pairs": len(mapping),
        "mapping_case_count": len(mapped_ids),
        "archive_labels": dict(Counter(labels.values())),
        "unmapped_cases": sorted(set(labels) - mapped_ids),
        "missing_mapped_cases": sorted(mapped_ids - set(labels)),
        "label_mismatches": mismatches,
    }


def mapping_ground_truth(mapping: dict[str, str]) -> dict[str, bool]:
    truth = {case_id: False for case_id in mapping}
    truth.update({case_id: True for case_id in mapping.values()})
    return truth


def _compiler_metrics(statuses: list[dict[str, Any]]) -> dict[str, Any]:
    phase1_reached = 0
    phase2_reached = 0
    reached_any = 0
    phase1_failures = 0
    phase2_failures = 0
    any_failure_cases = 0
    failing_attempts = 0
    initial_failure_cases = 0
    resolved = 0
    unresolved = 0
    resolution_attempts = Counter()
    repair_attempt_counts = []

    for status in statuses:
        events = [event for event in (status.get("compiler_events") or []) if event.get("execution_result_available", True)]
        phase1 = [event for event in events if event.get("phase") in {"phase1_initial", "phase1_repair"}]
        initial = next((event for event in phase1 if event.get("phase") == "phase1_initial"), None)
        repairs = [event for event in phase1 if event.get("phase") == "phase1_repair"]
        phase2 = [event for event in events if event.get("phase") == "phase2"]

        if initial:
            phase1_reached += 1
        if phase2:
            phase2_reached += 1
        if events:
            reached_any += 1

        if initial and initial.get("had_compiler_error"):
            phase1_failures += 1
            initial_failure_cases += 1
            repair_attempt_counts.append(len(repairs))
            first_success = next((event for event in repairs if not event.get("had_compiler_error")), None)
            if first_success is not None:
                resolved += 1
                attempt = int(first_success.get("repair_attempt") or repairs.index(first_success) + 1)
                resolution_attempts[attempt] += 1
            else:
                unresolved += 1

        if any(event.get("had_compiler_error") for event in phase2):
            phase2_failures += 1
        if any(event.get("had_compiler_error") for event in events):
            any_failure_cases += 1
        failing_attempts += sum(bool(event.get("had_compiler_error")) for event in events)

    return {
        "phase1_reached": phase1_reached,
        "phase1_initial_failures": phase1_failures,
        "phase1_initial_failure_rate": safe_div(phase1_failures, phase1_reached),
        "phase2_reached": phase2_reached,
        "phase2_failures": phase2_failures,
        "phase2_failure_rate": safe_div(phase2_failures, phase2_reached),
        "cases_with_compile_attempt": reached_any,
        "cases_with_any_compiler_failure": any_failure_cases,
        "combined_failure_rate": safe_div(any_failure_cases, reached_any),
        "compiler_failing_attempts": failing_attempts,
        "initial_failure_cases": initial_failure_cases,
        "repairs_resolved": resolved,
        "repair_resolution_rate": safe_div(resolved, initial_failure_cases),
        "repairs_unresolved": unresolved,
        "resolved_after_1": resolution_attempts[1],
        "resolved_after_2": resolution_attempts[2],
        "resolved_after_3": resolution_attempts[3],
        "mean_repair_attempts": statistics.mean(repair_attempt_counts) if repair_attempt_counts else None,
    }


def build_metrics(
    statuses: list[dict[str, Any]],
    expected_cases: int,
    mapping: dict[str, str],
    total_duration_seconds: float,
) -> dict[str, Any]:
    status_counts = Counter(status.get("status", "error") for status in statuses)
    scored = [status for status in statuses if status.get("status") == "scored"]

    tp = sum(status.get("ground_truth") is True and status.get("prediction") is True for status in scored)
    tn = sum(status.get("ground_truth") is False and status.get("prediction") is False for status in scored)
    fp = sum(status.get("ground_truth") is False and status.get("prediction") is True for status in scored)
    fn = sum(status.get("ground_truth") is True and status.get("prediction") is False for status in scored)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    accuracy = safe_div(tp + tn, len(scored))
    f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
    balanced = None if recall is None or specificity is None else (recall + specificity) / 2

    durations = [float(status["duration_seconds"]) for status in statuses if status.get("attempted") and status.get("duration_seconds") is not None]
    by_id = {status.get("case_id"): status for status in scored}
    complete_pairs = 0
    both_correct = 0
    for consistent_id, inconsistent_id in mapping.items():
        consistent = by_id.get(consistent_id)
        inconsistent = by_id.get(inconsistent_id)
        if consistent and inconsistent:
            complete_pairs += 1
            both_correct += consistent.get("prediction") is False and inconsistent.get("prediction") is True

    return {
        "coverage": {
            "expected": expected_cases,
            "processed": len(statuses),
            "unavailable": status_counts["skipped"],
            "attempted": sum(bool(status.get("attempted")) for status in statuses),
            "tool_errors": status_counts["error"],
            "compiled": sum(any(event.get("execution_result_available", True) for event in (status.get("compiler_events") or [])) for status in statuses),
            "scored": len(scored),
            "score_coverage": safe_div(len(scored), expected_cases),
        },
        "classification": {
            "TP": tp,
            "TN": tn,
            "FP": fp,
            "FN": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "specificity": specificity,
            "accuracy": accuracy,
            "balanced_accuracy": balanced,
            "complete_pairs": complete_pairs,
            "both_correct_pairs": both_correct,
            "pair_accuracy": safe_div(both_correct, complete_pairs),
        },
        "compiler": _compiler_metrics(statuses),
        "timing": {
            "total_seconds": total_duration_seconds,
            "total": format_duration(total_duration_seconds),
            "attempted_case_count": len(durations),
            "mean_case_seconds": statistics.mean(durations) if durations else None,
            "median_case_seconds": statistics.median(durations) if durations else None,
            "max_case_seconds": max(durations) if durations else None,
        },
    }


def _markdown_report(
    run_id: str,
    model: str,
    metrics: dict[str, Any],
    audit: dict[str, Any],
    statuses: list[dict[str, Any]],
    interrupted: bool,
) -> str:
    coverage = metrics["coverage"]
    classification = metrics["classification"]
    compiler = metrics["compiler"]
    timing = metrics["timing"]
    lines = [
        f"# CASCADE core benchmark — {run_id}",
        "",
        f"Model: `{model}`",
        f"Run state: **{'interrupted/partial' if interrupted else 'complete'}**",
        f"Runtime: **{timing['total']}**",
        "",
        "## Coverage",
        "",
        f"The core archive contains {coverage['expected']} cases. Processed {coverage['processed']}; "
        f"attempted {coverage['attempted']}; compiled {coverage['compiled']}; scored {coverage['scored']}; "
        f"unavailable/skipped {coverage['unavailable']}; tool errors {coverage['tool_errors']}.",
        "",
        "## Final phase-2 classification",
        "",
        f"TP={classification['TP']}, TN={classification['TN']}, FP={classification['FP']}, FN={classification['FN']}.",
        "",
        "| Precision | Recall | F1 | Specificity | Accuracy | Balanced accuracy |",
        "|---:|---:|---:|---:|---:|---:|",
        "| " + " | ".join(format_score(classification[field]) for field in CLASSIFICATION_FIELDS) + " |",
        "",
        f"Complete mapped pairs: {classification['complete_pairs']}; both members correctly classified: "
        f"{classification['both_correct_pairs']} ({format_score(classification['pair_accuracy'])}).",
        "",
        "## Compiler failures and repairs",
        "",
        f"- Phase 1 initial: {compiler['phase1_initial_failures']}/{compiler['phase1_reached']} cases "
        f"({format_percentage(compiler['phase1_initial_failure_rate'])}).",
        f"- Phase 2: {compiler['phase2_failures']}/{compiler['phase2_reached']} cases "
        f"({format_percentage(compiler['phase2_failure_rate'])}).",
        f"- Any phase: {compiler['cases_with_any_compiler_failure']}/{compiler['cases_with_compile_attempt']} cases "
        f"({format_percentage(compiler['combined_failure_rate'])}).",
        f"- Compiler-failing attempts, including repeated repairs: {compiler['compiler_failing_attempts']}.",
        f"- Initially failing phase-1 cases resolved: {compiler['repairs_resolved']}/{compiler['initial_failure_cases']}; "
        f"unresolved: {compiler['repairs_unresolved']}.",
        f"- Resolved after attempt 1/2/3: {compiler['resolved_after_1']}/"
        f"{compiler['resolved_after_2']}/{compiler['resolved_after_3']}; mean attempts among initial failures: "
        f"{format_score(compiler['mean_repair_attempts'])}.",
        "",
        "The compiler unit is a generated test class/case, not an individual test method. Raw Maven diagnostics are retained in per-case artifacts.",
        "",
        "## Timing",
        "",
        f"Attempted-case mean {format_duration(timing['mean_case_seconds'])}, median "
        f"{format_duration(timing['median_case_seconds'])}, maximum {format_duration(timing['max_case_seconds'])}.",
        "",
        "## Dataset integrity",
        "",
        f"Mapping pairs: {audit['mapping_pairs']}; archive labels: {audit['archive_labels']}; "
        f"mapping/archive label mismatches: {len(audit['label_mismatches'])}. Mapping-derived labels were used for scoring.",
    ]
    for mismatch in audit["label_mismatches"]:
        lines.append(
            f"- `{mismatch['case_id']}`: archive `{mismatch['archive_label']}`, mapping `{mismatch['mapping_label']}`."
        )

    excluded = [status for status in statuses if status.get("status") != "scored"]
    lines.extend(["", "## Excluded cases", ""])
    if not excluded:
        lines.append("None.")
    else:
        for status in excluded:
            lines.append(f"- `{status.get('case_id')}` — {status.get('status')}: {status.get('reason', 'unspecified')}.")
    lines.append("")
    return "\n".join(lines)


def _latex_artifacts(run_id: str, model: str, metrics: dict[str, Any]) -> tuple[dict[str, Any], str, str, str]:
    coverage = metrics["coverage"]
    classification = metrics["classification"]
    compiler = metrics["compiler"]
    timing = metrics["timing"]
    values = {
        "run": run_id,
        "model": model,
        "scored": coverage["scored"],
        "expected": coverage["expected"],
        "phase1_failures": compiler["phase1_initial_failures"],
        "phase1_reached": compiler["phase1_reached"],
        "phase2_failures": compiler["phase2_failures"],
        "phase2_reached": compiler["phase2_reached"],
        "any_failures": compiler["cases_with_any_compiler_failure"],
        "compile_cases": compiler["cases_with_compile_attempt"],
        "repairs_resolved": compiler["repairs_resolved"],
        "initial_failures": compiler["initial_failure_cases"],
        "mean_repairs": compiler["mean_repair_attempts"],
        "precision": classification["precision"],
        "recall": classification["recall"],
        "f1": classification["f1"],
        "accuracy": classification["accuracy"],
        "runtime_seconds": timing["total_seconds"],
    }
    row_parts = [
        latex_escape(run_id),
        latex_escape(model),
        f"{coverage['scored']}/{coverage['expected']}",
        format_rate(compiler["phase1_initial_failures"], compiler["phase1_reached"]),
        format_rate(compiler["phase2_failures"], compiler["phase2_reached"]),
        format_rate(compiler["cases_with_any_compiler_failure"], compiler["cases_with_compile_attempt"]),
        format_rate(compiler["repairs_resolved"], compiler["initial_failure_cases"]),
        "--" if compiler["mean_repair_attempts"] is None else f"{compiler['mean_repair_attempts']:.2f}",
        format_score(classification["precision"]),
        format_score(classification["recall"]),
        format_score(classification["f1"]),
        format_score(classification["accuracy"]),
        format_duration(timing["total_seconds"]),
    ]
    row = " &\n".join(row_parts) + r" \\" + "\n"
    header = (
        "Run & Model & Scored & P1 compiler failures & P2 compiler failures & Any compiler failure & "
        "Repairs resolved & Mean repairs & Precision & Recall & F1 & Accuracy & Runtime \\\\\n"
    )
    detail_header = (
        "Run & P1 initial failures & Resolved after 1 & Resolved after 2 & Resolved after 3 & "
        "Unresolved & P2 failures & Failing compile attempts \\\\\n"
    )
    detail_row = " & ".join(
        [
            latex_escape(run_id),
            str(compiler["phase1_initial_failures"]),
            str(compiler["resolved_after_1"]),
            str(compiler["resolved_after_2"]),
            str(compiler["resolved_after_3"]),
            str(compiler["repairs_unresolved"]),
            str(compiler["phase2_failures"]),
            str(compiler["compiler_failing_attempts"]),
        ]
    ) + r" \\" + "\n"
    table = f"""\\documentclass{{article}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\begin{{document}}
\\begin{{table}}[ht]
\\centering
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{llrrrrrrrrrrr}}
\\toprule
{header}\\midrule
{row}\\bottomrule
\\end{{tabular}}}}
\\caption{{CASCADE core benchmark results.}}
\\end{{table}}

\\begin{{table}}[ht]
\\centering
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{lrrrrrrr}}
\\toprule
{detail_header}\\midrule
{detail_row}\\bottomrule
\\end{{tabular}}}}
\\caption{{CASCADE compiler repair details.}}
\\end{{table}}
\\end{{document}}
"""
    return values, header, row, table


def write_reports(
    run_root: Path,
    statuses: list[dict[str, Any]],
    mapping: dict[str, str],
    audit: dict[str, Any],
    model: str,
    run_id: str,
    total_duration_seconds: float,
    interrupted: bool = False,
) -> dict[str, Any]:
    results_dir = run_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    metrics = build_metrics(statuses, audit["case_count"], mapping, total_duration_seconds)
    payload = {
        "run_id": run_id,
        "model": model,
        "interrupted": interrupted,
        "dataset_audit": audit,
        **metrics,
    }
    (results_dir / "metrics.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (results_dir / "report.md").write_text(
        _markdown_report(run_id, model, metrics, audit, statuses, interrupted), encoding="utf-8"
    )

    fields = [
        "index", "case_id", "ground_truth", "status", "reason", "prediction", "result",
        "attempted", "duration_seconds", "repository", "commit",
    ]
    with (results_dir / "cases.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(statuses)

    values, header, row, table = _latex_artifacts(run_id, model, metrics)
    (results_dir / "table_values.json").write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (results_dir / "table_header.tex").write_text(header, encoding="utf-8")
    (results_dir / "table_row.tex").write_text(row, encoding="utf-8")
    (results_dir / "table.tex").write_text(table, encoding="utf-8")
    return payload
