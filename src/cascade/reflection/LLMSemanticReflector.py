"""
reflection/LLMSemanticReflector.py
-----------------------------------
Implements the semantic explanation layer proposed in the design.

This reflector makes ONE focused LLM call that receives:
  • original_doc        – what the developer wrote
  • synthesized_doc     – what the LLM inferred the doc should say,
                          given the synthesized implementation
  • original_code       – the existing implementation (for context)
  • synthesized_code    – the implementation derived from the doc
  • diff_summary        – structured diff from DiffReflector (passed via extra)

It asks the model to:
  1. State in one sentence *what* is inconsistent.
  2. State in one sentence *which side* (code or doc) is likely wrong.
  3. Assign a confidence label (HIGH / MEDIUM / LOW).

The model is explicitly told NOT to reproduce large blocks of code so that
the output stays concise and usable as a developer-facing alert.

Can be run stand-alone or chained after DiffReflector in the pipeline.
"""

import json
import os
from typing import Optional

from .Reflector import InconsistencyType, ReflectionResult, Reflector


_SYSTEM_PROMPT = """\
You are a senior software-engineering assistant specialising in code–documentation \
inconsistency analysis.

You will receive:
- ORIGINAL_DOC: the Javadoc as it exists in the repository
- SYNTHESIZED_DOC: documentation regenerated from an LLM-synthesized implementation \
  that was derived solely from ORIGINAL_DOC
- ORIGINAL_CODE: the method body as it exists in the repository
- SYNTHESIZED_CODE: the method body the LLM synthesized from ORIGINAL_DOC
- DIFF_SUMMARY: a short structured summary of the code diff

Your task:
1. Identify the specific semantic discrepancy between ORIGINAL_DOC and ORIGINAL_CODE \
   by using SYNTHESIZED_CODE and SYNTHESIZED_DOC as documentation oracles.
2. Decide whether the documentation or the code is more likely to be wrong.
3. Classify the inconsistency into exactly one of these types:
   ReturnValueMismatch | BranchMismatch | ExceptionContractViolation |
   IterationMismatch | SideEffectContradiction | CaseSensitivityMismatch |
   NullHandlingMismatch | UnderdocumentedBehavior | Unknown

Respond ONLY with a JSON object, no prose outside the JSON, no markdown fences.
Schema:
{
  "inconsistency_type": "<one of the types above>",
  "explanation": "<one concise sentence for a developer, ≤ 40 words>",
  "likely_wrong_side": "code" | "doc" | "both" | "unclear",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "doc_delta_summary": "<one sentence describing how SYNTHESIZED_DOC differs from ORIGINAL_DOC, ≤ 30 words>"
}
"""

_CONFIDENCE_MAP = {"HIGH": 0.85, "MEDIUM": 0.55, "LOW": 0.30}


class LLMSemanticReflector(Reflector):
    """
    LLM-backed reflector that uses synthesized documentation as an oracle
    to produce precise natural-language explanations of inconsistencies.

    Config kwargs
    -------------
    model : str
        OpenAI model name.  Default: "gpt-4.1-mini".
    temperature : float
        Generation temperature.  Default: 0.0 (deterministic).
    require_synthesized_doc : bool
        If True and synthesized_doc is None, raise ValueError instead of
        falling back to a doc-diff-less prompt.  Default: False.
    confidence_boost_on_doc_delta : float
        Added to the LLM's base confidence when the synthesized_doc
        materially differs from the original_doc (token overlap < 0.6).
        Default: 0.1.
    """

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.0,
        require_synthesized_doc: bool = False,
        confidence_boost_on_doc_delta: float = 0.1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.temperature = temperature
        self.require_synthesized_doc = require_synthesized_doc
        self.confidence_boost_on_doc_delta = confidence_boost_on_doc_delta
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        except ImportError:
            self._client = None

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

        if self.require_synthesized_doc and synthesized_doc is None:
            raise ValueError(
                "LLMSemanticReflector requires synthesized_doc but none was provided. "
                "Add a DocGenerator step before this Reflector in your config, or set "
                "require_synthesized_doc=false."
            )

        diff_lines  = self.unified_diff(original_code, synthesized_code)
        diff_summary = extra.get("diff_summary", self._compact_diff(diff_lines))

        user_content = self._build_user_message(
            original_doc,
            synthesized_doc,
            original_code,
            synthesized_code,
            diff_summary,
        )

        if self._client is None:
            return ReflectionResult(
                inconsistency_type=InconsistencyType.UNKNOWN,
                explanation="openai package not installed; LLMSemanticReflector unavailable.",
                precision_confidence=0.3,
                code_diff_lines=self.unified_diff(original_code, synthesized_code),
                raw_metadata={"error": "openai_not_installed"},
            )

        # ----------------------------------------------------------------
        # LLM call
        # ----------------------------------------------------------------
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
            )
            raw_json = response.choices[0].message.content
            parsed   = json.loads(raw_json)
        except Exception as exc:
            # Never let a reflector crash the main pipeline — degrade gracefully.
            return ReflectionResult(
                inconsistency_type=InconsistencyType.UNKNOWN,
                explanation=f"LLMSemanticReflector failed: {exc}",
                precision_confidence=0.3,
                code_diff_lines=diff_lines,
                raw_metadata={"error": str(exc)},
            )

        # ----------------------------------------------------------------
        # Parse and enrich the LLM response
        # ----------------------------------------------------------------
        inco_type   = parsed.get("inconsistency_type", InconsistencyType.UNKNOWN)
        explanation = parsed.get("explanation", "")
        confidence_label = parsed.get("confidence", "LOW")
        base_confidence  = _CONFIDENCE_MAP.get(confidence_label, 0.3)
        doc_delta_summary = parsed.get("doc_delta_summary")

        # Doc-delta boost: if synthesized_doc materially diverges from
        # original_doc, the LLM found something the doc doesn't say,
        # which is extra evidence of a documentation-side problem.
        doc_delta_boost = 0.0
        if synthesized_doc:
            overlap = self.token_overlap_ratio(original_doc, synthesized_doc)
            if overlap < 0.6:
                doc_delta_boost = self.confidence_boost_on_doc_delta

        # Test-evidence boost (same logic as DiffReflector)
        total_tests = p2f_count + f2p_count
        pdr_bonus = min(p2f_count / (total_tests + 1), 0.15) if total_tests > 0 else 0.0

        final_confidence = min(0.97, base_confidence + doc_delta_boost + pdr_bonus)

        return ReflectionResult(
            inconsistency_type=inco_type,
            explanation=explanation,
            precision_confidence=round(final_confidence, 3),
            doc_delta_summary=doc_delta_summary,
            code_diff_lines=diff_lines,
            raw_metadata={
                "llm_raw": parsed,
                "likely_wrong_side": parsed.get("likely_wrong_side", "unclear"),
                "confidence_label": confidence_label,
                "doc_delta_boost": doc_delta_boost,
                "pdr_bonus": round(pdr_bonus, 3),
                "doc_token_overlap": (
                    round(self.token_overlap_ratio(original_doc, synthesized_doc), 3)
                    if synthesized_doc else None
                ),
                "p2f_count": p2f_count,
                "f2p_count": f2p_count,
            },
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compact_diff(diff_lines: list, max_lines: int = 30) -> str:
        """Truncate diff to avoid blowing up the context window."""
        lines = diff_lines[:max_lines]
        if len(diff_lines) > max_lines:
            lines.append(f"... ({len(diff_lines) - max_lines} more lines truncated)\n")
        return "".join(lines)

    @staticmethod
    def _build_user_message(
        original_doc: str,
        synthesized_doc: Optional[str],
        original_code: str,
        synthesized_code: str,
        diff_summary: str,
    ) -> str:
        synth_doc_block = (
            synthesized_doc if synthesized_doc
            else "(not available — a DocGenerator was not run in this pipeline)"
        )
        return (
            f"ORIGINAL_DOC:\n{original_doc}\n\n"
            f"SYNTHESIZED_DOC:\n{synth_doc_block}\n\n"
            f"ORIGINAL_CODE:\n{original_code}\n\n"
            f"SYNTHESIZED_CODE:\n{synthesized_code}\n\n"
            f"DIFF_SUMMARY (original → synthesized):\n{diff_summary}"
        )