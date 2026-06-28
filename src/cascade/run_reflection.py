#!/usr/bin/env python3
"""
run_reflection.py
-----------------
Standalone CLI that runs the reflection layer on an EXISTING analyzed.json
produced by CASCADE, without re-running extraction, filtering, or analysis.

Use this when you've already run:
    CASCADE run -i <project> -o <output> -c <config>

And you now want to add reflection on top of the results:
    python run_reflection.py -i <output>/analyzed.json -o <output> [options]

Usage
-----
    python run_reflection.py \\
        --input  ./exampleTargetproject/output/analyzed.json \\
        --output ./exampleTargetproject/output \\
        --reflector ChainedReflector \\
        --escalation-threshold 0.65 \\
        --model gpt-4.1-mini \\
        --only-flagged

Output files written
--------------------
    <output>/reflected.json          — full enriched analysis
    <output>/inconsistent_functions.json  — patched in-place (if present)
    <output>/reflection_report.txt   — human-readable comparison report
"""

import argparse
import json
import os
import sys

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.dirname(__file__))

from reflection import ChainedReflector, DiffReflector, LLMSemanticReflector
from reflection.ReflectionPipeline import ReflectionPipeline


def parse_args():
    p = argparse.ArgumentParser(
        description="Run the CASCADE reflection layer on an existing analyzed.json"
    )
    p.add_argument(
        "--input", "-i", required=True,
        help="Path to analyzed.json produced by CASCADE",
    )
    p.add_argument(
        "--output", "-o", required=True,
        help="Output directory (reflected.json will be written here)",
    )
    p.add_argument(
        "--reflector", default="ChainedReflector",
        choices=["DiffReflector", "LLMSemanticReflector", "ChainedReflector"],
        help="Which reflector to use (default: ChainedReflector)",
    )
    p.add_argument(
        "--escalation-threshold", type=float, default=0.65,
        help="ChainedReflector only: confidence threshold below which the LLM is called",
    )
    p.add_argument(
        "--model", default="gpt-4.1-mini",
        help="OpenAI model for LLMSemanticReflector / ChainedReflector LLM stage",
    )
    p.add_argument(
        "--only-flagged", action="store_true", default=True,
        help="Only reflect on INCO-labelled entries (default: True)",
    )
    p.add_argument(
        "--all", dest="only_flagged", action="store_false",
        help="Run reflection on all entries, not just INCO ones",
    )
    p.add_argument(
        "--no-report", action="store_true",
        help="Skip writing the human-readable comparison report",
    )
    return p.parse_args()


def build_reflector_kwargs(args) -> dict:
    if args.reflector == "DiffReflector":
        return {}
    if args.reflector == "LLMSemanticReflector":
        return {"model": args.model}
    # ChainedReflector
    return {
        "escalation_threshold": args.escalation_threshold,
        "llm_kwargs": {"model": args.model},
    }


def main():
    args = parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"[run_reflection] Input:     {args.input}")
    print(f"[run_reflection] Output:    {args.output}")
    print(f"[run_reflection] Reflector: {args.reflector}")
    print(f"[run_reflection] Only INCO: {args.only_flagged}")

    pipeline = ReflectionPipeline(
        reflector_name=args.reflector,
        reflector_kwargs=build_reflector_kwargs(args),
        only_flagged=args.only_flagged,
    )

    reflected_path = pipeline.run(
        analyzed_path=args.input,
        output_dir=args.output,
    )
    print(f"[run_reflection] Wrote: {reflected_path}")

    if not args.no_report:
        report_path = os.path.join(args.output, "reflection_report.txt")
        write_comparison_report(reflected_path, report_path)
        print(f"[run_reflection] Report: {report_path}")


def write_comparison_report(reflected_path: str, report_path: str):
    with open(reflected_path, "r") as f:
        reflected = json.load(f)
    analyzed = reflected   # reflected.json contains all original fields

    lines = []
    lines.append("=" * 72)
    lines.append("CASCADE REFLECTION REPORT")
    lines.append("=" * 72)
    lines.append(f"Source:    {reflected_path}")
    lines.append(f"Reflected: {reflected_path}")
    lines.append("")

    # ── Summary counts ────────────────────────────────────────────────
    total         = len(reflected)
    base_inco     = sum(1 for e in reflected  if e.get("prediction") == "INCO")
    base_noinco   = total - base_inco
    has_reflection = [e for e in reflected if e.get("reflection") and not e["reflection"].get("error")]

    lines.append("BASE CASCADE RESULTS")
    lines.append("-" * 40)
    lines.append(f"  Total methods analysed : {total}")
    lines.append(f"  Flagged INCO           : {base_inco}")
    lines.append(f"  Flagged NoInco         : {base_noinco}")
    lines.append("")

    # ── Reflection summary ────────────────────────────────────────────
    from collections import Counter
    type_counts  = Counter()
    side_counts  = Counter()
    confidences  = []
    high_conf    = 0   # confidence >= 0.75 → likely true positive
    low_conf     = 0   # confidence < 0.45  → likely false positive

    for entry in has_reflection:
        r = entry["reflection"]
        type_counts[r.get("inconsistency_type", "Unknown")] += 1
        side_counts[r.get("likely_wrong_side",  "unclear")] += 1
        conf = r.get("precision_confidence", 0.5)
        confidences.append(conf)
        if conf >= 0.75: high_conf += 1
        if conf <  0.45: low_conf  += 1

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    lines.append("REFLECTION LAYER RESULTS")
    lines.append("-" * 40)
    lines.append(f"  Entries reflected        : {len(has_reflection)}")
    lines.append(f"  Avg precision_confidence : {avg_conf:.3f}")
    lines.append(f"  High-confidence (≥0.75)  : {high_conf}  ← likely true positives")
    lines.append(f"  Low-confidence  (<0.45)  : {low_conf}  ← likely false positives")
    lines.append("")

    lines.append("  Inconsistency type breakdown:")
    for t, c in type_counts.most_common():
        lines.append(f"    {t:<35} {c}")
    lines.append("")

    lines.append("  Likely-wrong-side breakdown:")
    for s, c in side_counts.most_common():
        lines.append(f"    {str(s):<35} {c}")
    lines.append("")

    # ── PDR: do test failures match structural diff? ──────────────────
    lines.append("PRECISION DISAMBIGUATION RATE (PDR) ANALYSIS")
    lines.append("-" * 40)
    lines.append(
        "  PDR asks: for every p2f>0 entry, does the structural diff\n"
        "  directly explain why the synthesized implementation passes\n"
        "  tests that the original fails?\n"
    )

    pdr_explained   = 0   # INCO + reflection type not Unknown + p2f > 0
    pdr_unexplained = 0   # INCO + p2f > 0 but reflection type is Unknown
    pdr_no_tests    = 0   # INCO but p2f == 0

    for entry in reflected:
        if entry.get("prediction") != "INCO":
            continue
        p2f = int(entry.get("p2f", 0))
        r   = entry.get("reflection") or {}
        t   = r.get("inconsistency_type", "Unknown")

        if p2f > 0:
            if t != "Unknown" and not r.get("error"):
                pdr_explained += 1
            else:
                pdr_unexplained += 1
        else:
            pdr_no_tests += 1

    pdr_denominator = pdr_explained + pdr_unexplained
    pdr_score = pdr_explained / pdr_denominator if pdr_denominator > 0 else 0.0

    lines.append(f"  INCO entries with p2f>0   : {pdr_denominator}")
    lines.append(f"    Diff explains failure    : {pdr_explained}")
    lines.append(f"    Diff doesn't explain     : {pdr_unexplained}")
    lines.append(f"  INCO entries with p2f==0  : {pdr_no_tests}  (no test evidence)")
    lines.append(f"  PDR score                  : {pdr_score:.3f}  (higher = fewer unexplained flags)")
    lines.append("")

    # ── Per-entry detail ──────────────────────────────────────────────
    lines.append("PER-ENTRY DETAIL  (INCO only)")
    lines.append("-" * 72)
    lines.append(f"{'Method':<40} {'Type':<28} {'Conf':>6}  {'Side':<8}  {'p2f':>4}")
    lines.append("-" * 72)

    for entry in reflected:
        if entry.get("prediction") != "INCO":
            continue
        name = (entry.get("method_name") or entry.get("id") or "?")[:39]
        r    = entry.get("reflection") or {}
        if r.get("error"):
            lines.append(f"  {name:<40}  [reflection error: {r['error']}]")
            continue
        t    = (r.get("inconsistency_type") or "?")[:27]
        conf = r.get("precision_confidence", 0.0)
        side = (r.get("likely_wrong_side")  or "?")[:7]
        p2f  = entry.get("p2f", 0)
        lines.append(f"  {name:<40} {t:<28} {conf:>6.3f}  {side:<8}  {p2f:>4}")

    lines.append("")

    # ── Explanations ──────────────────────────────────────────────────
    lines.append("EXPLANATIONS  (INCO only, sorted by confidence ↓)")
    lines.append("-" * 72)

    inco_reflected = [
        e for e in reflected
        if e.get("prediction") == "INCO"
        and e.get("reflection")
        and not e["reflection"].get("error")
    ]
    inco_reflected.sort(
        key=lambda e: e["reflection"].get("precision_confidence", 0),
        reverse=True,
    )
    for entry in inco_reflected:
        r    = entry["reflection"]
        name = entry.get("method_name") or entry.get("id") or "?"
        conf = r.get("precision_confidence", 0.0)
        expl = r.get("explanation", "")
        ddoc = r.get("doc_delta_summary", "")
        lines.append(f"\n  [{conf:.3f}] {name}")
        lines.append(f"    → {expl}")
        if ddoc:
            lines.append(f"    Doc Δ: {ddoc}")

    lines.append("")
    lines.append("=" * 72)
    lines.append("END OF REPORT")
    lines.append("=" * 72)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()