"""
reflection/ChainedReflector.py
-------------------------------
Runs DiffReflector (cheap, deterministic) first.
Only escalates to LLMSemanticReflector when the structural confidence is
below a configurable threshold — saving LLM calls for clear-cut cases.

This is the recommended default reflector for production use.

Pipeline decision logic
-----------------------

  DiffReflector confidence ≥ escalation_threshold
      → return DiffReflector result directly (fast path)

  DiffReflector confidence < escalation_threshold
      → run LLMSemanticReflector and merge results:
          - take LLM's explanation and doc_delta_summary
          - take the higher of the two confidence scores
          - prefer LLM's inconsistency_type unless it is Unknown
"""

from typing import Optional

from .DiffReflector import DiffReflector
from .LLMSemanticReflector import LLMSemanticReflector
from .Reflector import InconsistencyType, ReflectionResult, Reflector


class ChainedReflector(Reflector):
    """
    Two-stage reflector: fast structural diff + optional LLM escalation.

    Config kwargs
    -------------
    escalation_threshold : float
        DiffReflector confidence below this value triggers LLM escalation.
        Default: 0.65.
    diff_kwargs : dict
        Forwarded to DiffReflector.__init__.
    llm_kwargs : dict
        Forwarded to LLMSemanticReflector.__init__.
    """

    def __init__(
        self,
        escalation_threshold: float = 0.65,
        diff_kwargs: Optional[dict] = None,
        llm_kwargs: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.escalation_threshold = escalation_threshold
        self._diff_reflector = DiffReflector(**(diff_kwargs or {}))
        self._llm_reflector  = LLMSemanticReflector(**(llm_kwargs or {}))

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

        # Stage 1 — always run the cheap diff pass
        diff_result = self._diff_reflector.reflect(
            original_code=original_code,
            synthesized_code=synthesized_code,
            original_doc=original_doc,
            synthesized_doc=synthesized_doc,
            p2f_count=p2f_count,
            f2p_count=f2p_count,
            **extra,
        )

        if diff_result.precision_confidence >= self.escalation_threshold:
            diff_result.raw_metadata["escalated_to_llm"] = False
            return diff_result

        # Stage 2 — escalate to LLM
        compact_diff = "".join(diff_result.code_diff_lines[:30])
        llm_result = self._llm_reflector.reflect(
            original_code=original_code,
            synthesized_code=synthesized_code,
            original_doc=original_doc,
            synthesized_doc=synthesized_doc,
            p2f_count=p2f_count,
            f2p_count=f2p_count,
            diff_summary=compact_diff,
            **extra,
        )

        # Merge: prefer LLM's richer output, but keep diff's code_diff_lines
        merged_confidence = max(diff_result.precision_confidence, llm_result.precision_confidence)

        merged_type = (
            llm_result.inconsistency_type
            if llm_result.inconsistency_type != InconsistencyType.UNKNOWN
            else diff_result.inconsistency_type
        )

        merged_explanation = llm_result.explanation or diff_result.explanation

        return ReflectionResult(
            inconsistency_type=merged_type,
            explanation=merged_explanation,
            precision_confidence=round(merged_confidence, 3),
            doc_delta_summary=llm_result.doc_delta_summary,
            code_diff_lines=diff_result.code_diff_lines,
            raw_metadata={
                "escalated_to_llm": True,
                "diff_stage": diff_result.raw_metadata,
                "llm_stage": llm_result.raw_metadata,
            },
        )