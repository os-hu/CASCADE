#!/usr/bin/env python3
"""
eval_with_reflection.py
------------------------
Drop-in companion to PaperEvaluation/eval.py.

Reads a reflected.json (or a directory containing one) and prints:

  1. BASE CASCADE metrics — identical to what eval.py computes, derived
     from the raw "prediction" + p2p/p2f/f2p/f2f counts already in the file.

  2. REFLECTION-ADJUSTED metrics — after applying a confidence threshold to
     suppress low-confidence INCO flags as false positives.

  3. DELTA table — shows exactly how the reflector changed each metric.

  4. PDR breakdown — per inconsistency-type precision disambiguation rate.

  5. Per-method diff — for every entry where the prediction changed, show
     what the reflector found and why.

Usage
-----
    # From a single reflected.json
    python eval_with_reflection.py --input ./output/reflected.json

    # From a directory (will find reflected.json inside)
    python eval_with_reflection.py --input ./output/

    # Adjust the confidence threshold for suppressing low-confidence flags
    python eval_with_reflection.py --input ./output/ --threshold 0.45

    # Match the original eval.py: also show per-method detail
    python eval_with_reflection.py --input ./output/ --verbose
"""

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MethodResult:
    method_name:     str
    ground_truth:    str        # "INCO" | "NoInco"  (from dataset label, may be absent)
    base_prediction: str        # "INCO" | "NoInco"
    p2p: int = 0
    p2f: int = 0
    f2p: int = 0
    f2f: int = 0
    reflection: dict = field(default_factory=dict)

    @property
    def reflection_confidence(self) -> float:
        return (self.reflection or {}).get("precision_confidence", 0.5)

    @property
    def reflection_type(self) -> str:
        return (self.reflection or {}).get("inconsistency_type", "Unknown")

    @property
    def reflection_prediction(self) -> Optional[str]:
        """None when reflection is absent."""
        if not self.reflection:
            return None
        return self.reflection.get("prediction_override")  # set by adjusted_prediction()

    def adjusted_prediction(self, threshold: float) -> str:
        """
        Apply confidence threshold:
        - If base says INCO but reflection confidence < threshold → suppress to NoInco
        - Otherwise keep base prediction
        """
        if self.base_prediction == "INCO" and self.reflection:
            if not self.reflection.get("error") and self.reflection_confidence < threshold:
                return "NoInco"
        return self.base_prediction


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class Metrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / total if total > 0 else 0.0

    def __str__(self):
        return (
            f"Precision={self.precision:.3f}  Recall={self.recall:.3f}  "
            f"F1={self.f1:.3f}  Accuracy={self.accuracy:.3f}  "
            f"(TP={self.tp} FP={self.fp} FN={self.fn} TN={self.tn})"
        )


def compute_metrics(results: List[MethodResult], predictions: List[str]) -> Metrics:
    """Compute metrics given ground-truth labels and a list of prediction strings."""
    m = Metrics()
    for result, pred in zip(results, predictions):
        gt = result.ground_truth
        if gt == "INCO"   and pred == "INCO":   m.tp += 1
        elif gt == "INCO" and pred == "NoInco": m.fn += 1
        elif gt == "NoInco" and pred == "INCO": m.fp += 1
        else:                                    m.tn += 1
    return m


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_reflected(path: str) -> List[MethodResult]:
    if os.path.isdir(path):
        path = os.path.join(path, "reflected.json")
    if not os.path.isfile(path):
        print(f"ERROR: {path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    results = []
    for entry in raw:
        # Ground truth: CASCADE's dataset stores it as "label" or "ground_truth"
        gt = entry.get("label") or entry.get("ground_truth") or entry.get("gt")
        if gt is None:
            # If not present, we can still show relative metrics
            gt = "UNKNOWN"

        name = entry.get("method_name") or entry.get("id") or "?"
        results.append(MethodResult(
            method_name=name,
            ground_truth=gt,
            base_prediction=entry.get("prediction", "NoInco"),
            p2p=int(entry.get("p2p", 0)),
            p2f=int(entry.get("p2f", 0)),
            f2p=int(entry.get("f2p", 0)),
            f2f=int(entry.get("f2f", 0)),
            reflection=entry.get("reflection") or {},
        ))
    return results


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

SEP  = "=" * 72
SEP2 = "-" * 72
W    = 72


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def row(label: str, value: str, width: int = 38):
    print(f"  {label:<{width}} {value}")


def delta_str(base: float, adj: float) -> str:
    d = adj - base
    sign = "+" if d >= 0 else ""
    return f"{adj:.3f}  ({sign}{d:.3f})"


# ---------------------------------------------------------------------------
# Main report
# ---------------------------------------------------------------------------

def run_eval(input_path: str, threshold: float, verbose: bool, no_ground_truth: bool):

    results = load_reflected(input_path)
    has_gt  = any(r.ground_truth not in ("UNKNOWN", None) for r in results)

    base_preds = [r.base_prediction for r in results]
    adj_preds  = [r.adjusted_prediction(threshold) for r in results]

    # ── Header ────────────────────────────────────────────────────────
    section("CASCADE + REFLECTION  —  EVALUATION REPORT")
    row("Input", input_path)
    row("Total methods", str(len(results)))
    row("Confidence threshold", f"{threshold:.2f}  (INCO flags below this are suppressed)")
    row("Ground truth available", "YES" if has_gt else "NO  (showing prediction-only stats)")
    print()

    # ── Base CASCADE stats ─────────────────────────────────────────────
    section("1. BASE CASCADE RESULTS  (no reflection)")
    base_inco   = sum(1 for p in base_preds if p == "INCO")
    base_noinco = len(base_preds) - base_inco
    row("Flagged INCO",   str(base_inco))
    row("Flagged NoInco", str(base_noinco))

    if has_gt:
        base_metrics = compute_metrics(results, base_preds)
        print()
        row("Precision",  f"{base_metrics.precision:.3f}")
        row("Recall",     f"{base_metrics.recall:.3f}")
        row("F1",         f"{base_metrics.f1:.3f}")
        row("Accuracy",   f"{base_metrics.accuracy:.3f}")
        row("TP / FP / FN / TN",
            f"{base_metrics.tp} / {base_metrics.fp} / {base_metrics.fn} / {base_metrics.tn}")

    # p2f / f2p totals as CASCADE's eval.py shows them
    total_p2f = sum(r.p2f for r in results if r.base_prediction == "INCO")
    total_f2p = sum(r.f2p for r in results if r.base_prediction == "INCO")
    total_p2p = sum(r.p2p for r in results if r.base_prediction == "INCO")
    total_f2f = sum(r.f2f for r in results if r.base_prediction == "INCO")
    print()
    row("Test-count totals (INCO entries)", "")
    row("  p2p  (pass→pass)",  str(total_p2p), 40)
    row("  f2p  (fail→pass)",  str(total_f2p), 40)
    row("  p2f  (pass→fail)",  str(total_p2f), 40)
    row("  f2f  (fail→fail)",  str(total_f2f), 40)

    # ── Reflection stats ───────────────────────────────────────────────
    section("2. REFLECTION LAYER RESULTS")

    reflected = [r for r in results if r.reflection and not r.reflection.get("error")]
    confidences = [r.reflection_confidence for r in reflected]
    avg_conf    = sum(confidences) / len(confidences) if confidences else 0.0
    high_conf   = sum(1 for c in confidences if c >= 0.75)
    low_conf    = sum(1 for c in confidences if c <  0.45)
    suppressed  = sum(1 for r, p in zip(results, adj_preds)
                      if r.base_prediction == "INCO" and p == "NoInco")

    row("Entries reflected",          str(len(reflected)))
    row("Avg precision_confidence",   f"{avg_conf:.3f}")
    row("High-conf flags (≥0.75)",    f"{high_conf}  ← likely true positives")
    row("Low-conf flags  (<0.45)",    f"{low_conf}  ← likely false positives")
    row("Suppressed by threshold",    f"{suppressed}  (INCO → NoInco after reflection)")
    print()

    type_counts = Counter(r.reflection_type for r in reflected)
    side_counts = Counter(
        (r.reflection.get("likely_wrong_side") or "unclear") for r in reflected
    )
    print(f"  {'Inconsistency type':<35} {'Count':>5}")
    print(f"  {'-'*35} {'-----':>5}")
    for t, c in type_counts.most_common():
        print(f"  {t:<35} {c:>5}")
    print()
    print(f"  {'Likely-wrong side':<35} {'Count':>5}")
    print(f"  {'-'*35} {'-----':>5}")
    for s, c in side_counts.most_common():
        print(f"  {s:<35} {c:>5}")

    # ── Adjusted predictions ───────────────────────────────────────────
    section("3. REFLECTION-ADJUSTED RESULTS  (threshold=" + f"{threshold:.2f})")
    adj_inco   = sum(1 for p in adj_preds if p == "INCO")
    adj_noinco = len(adj_preds) - adj_inco
    row("Flagged INCO   (adjusted)", str(adj_inco))
    row("Flagged NoInco (adjusted)", str(adj_noinco))

    if has_gt:
        adj_metrics = compute_metrics(results, adj_preds)
        print()
        row("Precision",  f"{adj_metrics.precision:.3f}")
        row("Recall",     f"{adj_metrics.recall:.3f}")
        row("F1",         f"{adj_metrics.f1:.3f}")
        row("Accuracy",   f"{adj_metrics.accuracy:.3f}")
        row("TP / FP / FN / TN",
            f"{adj_metrics.tp} / {adj_metrics.fp} / {adj_metrics.fn} / {adj_metrics.tn}")

    # ── Delta ──────────────────────────────────────────────────────────
    if has_gt:
        section("4. DELTA  (reflection-adjusted  minus  base CASCADE)")
        print(f"  {'Metric':<20} {'Base':>8}  {'Adjusted':>8}  {'Delta':>10}")
        print(f"  {'-'*20} {'----':>8}  {'--------':>8}  {'-----':>10}")
        for label, base_v, adj_v in [
            ("Precision",  base_metrics.precision, adj_metrics.precision),
            ("Recall",     base_metrics.recall,    adj_metrics.recall),
            ("F1",         base_metrics.f1,        adj_metrics.f1),
            ("Accuracy",   base_metrics.accuracy,  adj_metrics.accuracy),
        ]:
            d    = adj_v - base_v
            sign = "+" if d >= 0 else ""
            print(f"  {label:<20} {base_v:>8.3f}  {adj_v:>8.3f}  {sign}{d:>9.3f}")

        print()
        fp_base = base_metrics.fp
        fp_adj  = adj_metrics.fp
        fn_base = base_metrics.fn
        fn_adj  = adj_metrics.fn
        row("False positives reduced", f"{fp_base} → {fp_adj}  (Δ {fp_adj-fp_base:+d})")
        row("False negatives change",  f"{fn_base} → {fn_adj}  (Δ {fn_adj-fn_base:+d})")

    # ── PDR ───────────────────────────────────────────────────────────
    section("5. PRECISION DISAMBIGUATION RATE (PDR)")
    print(
        "  For every INCO entry with p2f>0:\n"
        "  does the structural diff explain which specific tests flip?\n"
    )
    pdr_explained   = 0
    pdr_unexplained = 0
    pdr_no_tests    = 0
    pdr_by_type: dict = {}

    for r in results:
        if r.base_prediction != "INCO":
            continue
        if r.p2f > 0:
            t = r.reflection_type
            if t != "Unknown" and r.reflection and not r.reflection.get("error"):
                pdr_explained += 1
                pdr_by_type[t] = pdr_by_type.get(t, {"explained": 0, "total": 0})
                pdr_by_type[t]["explained"] += 1
                pdr_by_type[t]["total"]     += 1
            else:
                pdr_unexplained += 1
                pdr_by_type.setdefault("Unknown", {"explained": 0, "total": 0})
                pdr_by_type["Unknown"]["total"] += 1
        else:
            pdr_no_tests += 1

    denom = pdr_explained + pdr_unexplained
    pdr   = pdr_explained / denom if denom > 0 else 0.0

    row("INCO entries with p2f>0",  str(denom))
    row("  Diff explains failure",  str(pdr_explained))
    row("  Diff doesn't explain",   str(pdr_unexplained))
    row("INCO entries with p2f==0", str(pdr_no_tests))
    row("PDR score",                f"{pdr:.3f}  (1.0 = all failures explained by diff)")
    print()

    if pdr_by_type:
        print(f"  {'Type':<35} {'PDR':>6}  {'Explained':>10}  {'Total':>6}")
        print(f"  {'-'*35} {'---':>6}  {'----------':>10}  {'-----':>6}")
        for t, counts in sorted(pdr_by_type.items()):
            type_pdr = counts["explained"] / counts["total"] if counts["total"] else 0.0
            print(f"  {t:<35} {type_pdr:>6.3f}  {counts['explained']:>10}  {counts['total']:>6}")

    # ── Changed predictions ────────────────────────────────────────────
    changed = [
        (r, bp, ap)
        for r, bp, ap in zip(results, base_preds, adj_preds)
        if bp != ap
    ]

    section(f"6. PREDICTION CHANGES  ({len(changed)} entries changed)")
    if not changed:
        print("  No predictions changed at this threshold.")
    else:
        print(f"  {'Method':<40} {'Base':<10} {'Adjusted':<10} {'Conf':>6}")
        print(f"  {'-'*72}")
        for r, bp, ap in changed:
            print(
                f"  {r.method_name[:39]:<40} {bp:<10} {ap:<10} "
                f"{r.reflection_confidence:>6.3f}"
            )

    # ── Per-entry verbose ──────────────────────────────────────────────
    if verbose:
        section("7. PER-ENTRY DETAIL  (INCO, sorted by confidence ↓)")
        print(
            f"  {'Method':<38} {'Type':<26} {'Conf':>6}  "
            f"{'Side':<8}  {'p2f':>4}  {'Adj':>6}"
        )
        print(f"  {'-'*72}")

        inco_results = sorted(
            [(r, ap) for r, ap in zip(results, adj_preds) if r.base_prediction == "INCO"],
            key=lambda x: x[0].reflection_confidence,
            reverse=True,
        )
        for r, ap in inco_results:
            if r.reflection.get("error"):
                print(f"  {r.method_name[:37]:<38}  [error: {r.reflection['error']}]")
                continue
            t    = r.reflection_type[:25]
            conf = r.reflection_confidence
            side = (r.reflection.get("likely_wrong_side") or "?")[:7]
            print(
                f"  {r.method_name[:37]:<38} {t:<26} {conf:>6.3f}  "
                f"{side:<8}  {r.p2f:>4}  {ap:>6}"
            )

        print()
        print("  EXPLANATIONS (sorted by confidence ↓)")
        print(f"  {'-'*72}")
        for r, _ in inco_results:
            if r.reflection.get("error"):
                continue
            expl = r.reflection.get("explanation", "")
            ddoc = r.reflection.get("doc_delta_summary", "")
            print(f"\n  [{r.reflection_confidence:.3f}] {r.method_name}")
            print(f"    → {expl}")
            if ddoc:
                print(f"    Doc Δ: {ddoc}")

    print(f"\n{SEP}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Evaluate CASCADE + reflection results against base CASCADE metrics"
    )
    p.add_argument(
        "--input", "-i", required=True,
        help="Path to reflected.json or directory containing it",
    )
    p.add_argument(
        "--threshold", "-t", type=float, default=0.45,
        help="Confidence threshold below which INCO flags are suppressed (default: 0.45)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-entry detail and explanations",
    )
    p.add_argument(
        "--no-ground-truth", action="store_true",
        help="Skip precision/recall computation even if ground truth is present",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_eval(
        input_path=args.input,
        threshold=args.threshold,
        verbose=args.verbose,
        no_ground_truth=args.no_ground_truth,
    )