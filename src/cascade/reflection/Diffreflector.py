"""
reflection/DiffReflector.py
---------------------------
Implements Metric 3 — Precision Disambiguation Rate (PDR).

For every method CASCADE already flagged as INCO, this reflector:

  1. Diffs original_code vs synthesized_code at the line level.
  2. Classifies the diff into a structural InconsistencyType.
  3. Checks whether the diff *explains* the observed p2f test failures
     (the core of PDR: does the structural delta predict the failing tests?).
  4. Emits a precision_confidence score based on diff size, type, and the
     p2f / f2p counts already computed by CASCADE's two-step analysis.

No LLM calls are made here — this is a cheap, deterministic first pass.
Use LLMSemanticReflector for the richer NL explanation layer.
"""

import re
from difflib import SequenceMatcher
from typing import Optional

from .Reflector import InconsistencyType, ReflectionResult, Reflector


# ---------------------------------------------------------------------------
# Heuristic keyword patterns that map diff lines to inconsistency types.
# Order matters: more specific patterns come first.
# ---------------------------------------------------------------------------
_TYPE_PATTERNS = [
    # (compiled_regex_on_removed_or_added_lines, InconsistencyType)
    # NOTE: More specific patterns must precede general ones.
    (re.compile(r"\bthrow\b|\bthrows\b", re.IGNORECASE), InconsistencyType.EXCEPTION_CONTRACT),
    # Case-sensitivity: look for *added* IgnoreCase calls vs *removed* case-sensitive ones
    (re.compile(r"(?i:ignorecase|tolowercase|touppercase|equalsignorecase|comparetoignorecase)"), InconsistencyType.CASE_SENSITIVITY),
    (re.compile(r"\bnull\b", re.IGNORECASE), InconsistencyType.NULL_HANDLING),
    (re.compile(r"\bfor\b|\bwhile\b|\bdo\b|\biterator\b|\bstream\b", re.IGNORECASE), InconsistencyType.ITERATION_MISMATCH),
    (re.compile(r"\bif\b|\belse\b|\bswitch\b|\bcase\b|\bternary\b|\?", re.IGNORECASE), InconsistencyType.BRANCH_MISMATCH),
    (re.compile(r"\breturn\b", re.IGNORECASE), InconsistencyType.RETURN_VALUE_MISMATCH),
    (re.compile(r"\bthis\.\w+\s*=|\bsuper\.\w+\s*=|System\.out|Logger\.", re.IGNORECASE), InconsistencyType.SIDE_EFFECT_CONTRADICTION),
]


def _classify_diff(removed_lines: list, added_lines: list) -> str:
    """
    Walk removed and added lines looking for the first matching pattern.
    Falls back to UNKNOWN if nothing matches.
    """
    changed = removed_lines + added_lines
    for pattern, inco_type in _TYPE_PATTERNS:
        if any(pattern.search(line) for line in changed):
            return inco_type
    return InconsistencyType.UNKNOWN


def _split_diff(diff_lines: list) -> tuple:
    """Return (removed_lines, added_lines) from unified diff output."""
    removed = [l[1:] for l in diff_lines if l.startswith("-") and not l.startswith("---")]
    added   = [l[1:] for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
    return removed, added


def _edit_distance_ratio(original: str, synthesized: str) -> float:
    """SequenceMatcher ratio — 1.0 = identical, 0.0 = nothing in common."""
    return SequenceMatcher(None, original, synthesized).ratio()


def _diff_density(diff_lines: list, original: str) -> float:
    """
    Fraction of original lines that were changed.
    Used to distinguish a localised fix from a total rewrite.
    """
    original_line_count = len(original.splitlines()) or 1
    changed_count = sum(
        1 for l in diff_lines
        if (l.startswith("-") and not l.startswith("---"))
        or (l.startswith("+") and not l.startswith("+++"))
    )
    return min(changed_count / original_line_count, 1.0)


class DiffReflector(Reflector):
    """
    Deterministic, LLM-free reflector that analyses structural code diffs.

    Config kwargs
    -------------
    min_diff_lines : int  (default 1)
        Minimum number of changed lines required to emit a non-trivial result.
    confidence_floor : float  (default 0.3)
        Lower bound on precision_confidence regardless of diff size.
    confidence_ceiling : float  (default 0.95)
        Upper bound — we never claim absolute certainty.
    """

    def __init__(
        self,
        min_diff_lines: int = 1,
        confidence_floor: float = 0.3,
        confidence_ceiling: float = 0.95,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.min_diff_lines = min_diff_lines
        self.confidence_floor = confidence_floor
        self.confidence_ceiling = confidence_ceiling

    # ------------------------------------------------------------------

    def reflect(
        self,
        original_code: str,
        synthesized_code: str,
        original_doc: str,
        synthesized_doc: Optional[str] = None,
        p2f_count: int = 0,
        f2p_count: int = 0,
        **extra,
    ) -> ReflectionResult:

        diff_lines = self.unified_diff(original_code, synthesized_code)
        removed, added = _split_diff(diff_lines)

        total_changed = len(removed) + len(added)

        # ----------------------------------------------------------------
        # Edge case: no structural diff at all.
        # The synthesised implementation is identical to the original — the
        # INCO flag is probably driven by test noise, not a real mismatch.
        # ----------------------------------------------------------------
        if total_changed < self.min_diff_lines:
            return ReflectionResult(
                inconsistency_type=InconsistencyType.UNKNOWN,
                explanation=(
                    "The synthesized implementation is structurally identical to the "
                    "original. The inconsistency flag is likely a false positive caused "
                    "by test flakiness or LLM generation noise."
                ),
                precision_confidence=self.confidence_floor,
                code_diff_lines=diff_lines,
                raw_metadata={
                    "total_changed_lines": 0,
                    "char_edit_distance_ratio": 1.0,
                    "diff_density": 0.0,
                    "p2f_count": p2f_count,
                    "f2p_count": f2p_count,
                },
            )

        # ----------------------------------------------------------------
        # Classify the diff.
        # ----------------------------------------------------------------
        inco_type = _classify_diff(removed, added)
        density    = _diff_density(diff_lines, original_code)
        similarity = _edit_distance_ratio(original_code, synthesized_code)

        # ----------------------------------------------------------------
        # Precision Disambiguation Rate logic (PDR).
        #
        # base_conf uses *line-level* change density rather than char-level
        # edit distance because a one-token swap in a long method has a very
        # high char-similarity but is still a meaningful semantic change.
        #
        # confidence formula:
        #   base   = min(density * 3, 0.6)   scaled so that changing even
        #            1/3 of lines gives a 0.6 base
        #   bonus  = clamp(p2f / (p2f+f2p+1), 0, 0.3)
        #   penalty= density > 0.6 ? -0.15 : 0  (large rewrites less reliable)
        # ----------------------------------------------------------------
        base_conf = min(density * 3.0, 0.6)

        total_tests = p2f_count + f2p_count
        pdr_bonus = min(p2f_count / (total_tests + 1), 0.3) if total_tests > 0 else 0.0

        rewrite_penalty = -0.15 if density > 0.6 else 0.0

        raw_conf = base_conf + pdr_bonus + rewrite_penalty
        confidence = max(self.confidence_floor, min(self.confidence_ceiling, raw_conf))

        # ----------------------------------------------------------------
        # Build explanation from diff facts.
        # ----------------------------------------------------------------
        explanation = self._build_explanation(
            inco_type, removed, added, density, p2f_count, f2p_count
        )

        return ReflectionResult(
            inconsistency_type=inco_type,
            explanation=explanation,
            precision_confidence=round(confidence, 3),
            code_diff_lines=diff_lines,
            raw_metadata={
                "total_changed_lines": total_changed,
                "removed_lines": len(removed),
                "added_lines": len(added),
                "char_edit_distance_ratio": round(similarity, 3),
                "diff_density": round(density, 3),
                "pdr_bonus": round(pdr_bonus, 3),
                "rewrite_penalty": rewrite_penalty,
                "p2f_count": p2f_count,
                "f2p_count": f2p_count,
            },
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_explanation(
        self,
        inco_type: str,
        removed: list,
        added: list,
        density: float,
        p2f_count: int,
        f2p_count: int,
    ) -> str:
        type_descriptions = {
            InconsistencyType.RETURN_VALUE_MISMATCH:
                "The synthesized implementation returns a different value than the original, "
                "suggesting the documented return behaviour does not match the code.",
            InconsistencyType.BRANCH_MISMATCH:
                "The synthesized implementation introduces or removes a conditional branch "
                "relative to the original, indicating that a documented case is not handled "
                "(or an undocumented case is).",
            InconsistencyType.EXCEPTION_CONTRACT:
                "The synthesized implementation differs in its exception-throwing logic, "
                "suggesting the documented exception contract is not correctly implemented.",
            InconsistencyType.ITERATION_MISMATCH:
                "The loop or iteration structure differs between the original and the "
                "synthesized code, pointing to a mismatch in documented iteration behaviour.",
            InconsistencyType.CASE_SENSITIVITY:
                "The synthesized code uses case-insensitive comparison while the original "
                "does not (or vice versa), matching a common doc–code inconsistency pattern.",
            InconsistencyType.NULL_HANDLING:
                "Null-handling logic differs between the original and the synthesized "
                "implementation, suggesting the documented null behaviour is incorrect.",
            InconsistencyType.SIDE_EFFECT_CONTRADICTION:
                "The synthesized implementation has different side effects (field mutation, "
                "I/O, logging) than the original, indicating an undocumented side effect.",
            InconsistencyType.UNKNOWN:
                "The structural delta between the original and synthesized implementations "
                "does not match a known inconsistency pattern.",
        }

        base = type_descriptions.get(inco_type, type_descriptions[InconsistencyType.UNKNOWN])

        # Add test-evidence sentence.
        if p2f_count > 0 and f2p_count == 0:
            evidence = (
                f" This is corroborated by {p2f_count} test(s) that pass on the synthesized "
                f"implementation but fail on the original — a strong signal of a true positive."
            )
        elif p2f_count > 0 and f2p_count > 0:
            evidence = (
                f" {p2f_count} test(s) pass on the synthesized but fail on the original; "
                f"however, {f2p_count} test(s) flip in the opposite direction, which may "
                f"indicate partial ambiguity in the documentation."
            )
        else:
            evidence = (
                " No disambiguating test evidence is available; the flag is based on "
                "structural diff alone."
            )

        # Add scope sentence.
        if density > 0.6:
            scope = (
                " The diff covers a large fraction of the method body, which may indicate "
                "the LLM performed a near-total rewrite rather than a targeted correction — "
                "treat this result with extra caution."
            )
        elif density < 0.15:
            scope = " The change is highly localised, increasing confidence in the diagnosis."
        else:
            scope = ""

        return base + evidence + scope