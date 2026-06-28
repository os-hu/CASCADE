"""
reflection/ReflectionAnalysis.py
---------------------------------
A CASCADE Analysis subclass that:
  1. Delegates the full two-step analysis to a wrapped inner Analysis
     (e.g. JavaTwoStepAnalysis) to produce synthesized code and test results.
  2. Immediately runs a Reflector on every flagged result BEFORE writing
     the output files, so that reflected.json and the enriched
     inconsistent_functions.json are produced as part of the normal
     CASCADE pipeline run — no separate post-processing step needed.

Extension point
---------------
Follows the exact pattern described in the CASCADE README:
  - Inherit from analysis/Analysis.py
  - Place file in analysis/ (or reference via --module-path)
  - Reference by class name in config under "analysis"

Config example
--------------
{
  "analysis": {
    "name": "ReflectionAnalysis",
    "kwargs": {
      "inner_analysis": {
        "name": "JavaTwoStepAnalysis",
        "kwargs": {
          "regenerate": false,
          "max_repair_tries": 3
        }
      },
      "reflector": {
        "name": "DiffExplainer",
        "kwargs": {
          "model": "gpt-4o-mini-2024-07-18",
          "temperature": 0.1
        }
      },
      "only_flagged": true
    }
  }
}

Note: generator and executor are NOT listed under inner_analysis.kwargs —
PipelineFactory passes them as the first two positional args to ReflectionAnalysis,
which then forwards them to the inner analysis.  Only extra kwargs like
regenerate/max_repair_tries belong in inner_analysis.kwargs.

How the inner_analysis is loaded
---------------------------------
PipelineFactory already uses dynamic class loading by name.  We replicate
that pattern here so this class is self-contained and does not import
JavaTwoStepAnalysis directly (keeping language-independence intact).
"""

import importlib
import json
import logging
import os

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.generation.Generation import Generation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Class loader — mirrors PipelineFactory's own dynamic-import pattern
# ---------------------------------------------------------------------------

def _load_class(name: str, search_packages: list):
    """
    Try to import `name` from each package in `search_packages` in order.
    Falls back to a bare import (for classes passed via --module-path).
    """
    for pkg in search_packages:
        try:
            module = importlib.import_module(f"{pkg}.{name}")
            return getattr(module, name)
        except (ModuleNotFoundError, AttributeError):
            continue
    # last resort: bare module name (e.g. when --module-path is used)
    module = importlib.import_module(name)
    return getattr(module, name)


def _build_inner_analysis(cfg: dict, generator: Generation, executor: Execution):
    """
    Instantiate an inner Analysis from a {name, kwargs} config dict.

    generator and executor are forwarded because every Analysis subclass
    (including JavaTwoStepAnalysis) requires them as the first two positional
    arguments — they are NOT part of the config kwargs.
    """
    name   = cfg["name"]
    kwargs = cfg.get("kwargs", {})
    cls = _load_class(name, [
        "cascade.analysis",
        "src.cascade.analysis",
    ])
    return cls(generator, executor, **kwargs)


def _build_reflector(cfg: dict):
    """Instantiate a Reflector subclass from a {name, kwargs} config dict."""
    name   = cfg["name"]
    kwargs = cfg.get("kwargs", {})
    cls = _load_class(name, [
        "cascade.reflection",
        "cascade.generation.explanation",   # DiffExplainer lives here
        "reflection",
    ])
    return cls(**kwargs)


# ---------------------------------------------------------------------------
# ReflectionAnalysis
# ---------------------------------------------------------------------------

class ReflectionAnalysis(Analysis):
    """
    Wraps any CASCADE Analysis and adds a post-analysis reflection pass.
    """

    def __init__(self,
                 generator:  Generation,
                 executor:   Execution,
                 inner_analysis=None,
                 reflector=None,
                 only_flagged: bool = True,
                 # ── field-name overrides (defaults match CASCADE's actual keys) ──
                 input_key_code:       str = "code",          # d["code"]       original body
                 input_key_synth_code: str = "new_code",      # d["new_code"]   synthesised body
                 input_key_doc:        str = "documentation", # d["documentation"]
                 input_key_synth_doc:  str = None             # no CASCADE equivalent; passed through to Reflector if present
                 ):
        super().__init__(generator, executor)

        # ── inner analysis ────────────────────────────────────────────────────
        # Accepts either a config dict (from JSON) or an already-built instance.
        if isinstance(inner_analysis, dict):
            self.inner_analysis = _build_inner_analysis(
                inner_analysis, generator, executor
            )
        elif inner_analysis is not None:
            # Caller passed a pre-built Analysis object directly
            self.inner_analysis = inner_analysis
        else:
            # Sensible default: the standard two-step Java analysis
            from cascade.analysis.JavaTwoStepAnalysis import JavaTwoStepAnalysis
            self.inner_analysis = JavaTwoStepAnalysis(generator, executor)

        # ── reflector ────────────────────────────────────────────────────────
        if isinstance(reflector, dict):
            self.reflector = _build_reflector(reflector)
        else:
            self.reflector = reflector  # pre-built or None

        self.only_flagged         = only_flagged
        self.input_key_code       = input_key_code
        self.input_key_synth_code = input_key_synth_code
        self.input_key_doc        = input_key_doc
        self.input_key_synth_doc  = input_key_synth_doc

    # -------------------------------------------------------------------------
    # CASCADE Analysis protocol
    # -------------------------------------------------------------------------

    def analyze(self, data: list, input_path: str, output_path: str) -> list:
        """
        Run the inner analysis, then attach reflection results in-memory.

        JavaTwoStepAnalysis.analyze() mutates `data` in-place and has no
        return statement, so we call it for its side-effects, then work with
        `data` directly.
        """
        logger.info(
            "[ReflectionAnalysis] Running inner analysis: %s",
            type(self.inner_analysis).__name__,
        )
        # BUG FIX 1: inner analysis mutates data in-place; it returns None.
        # Do NOT assign its return value — use `data` after the call.
        self.inner_analysis.analyze(data, input_path, output_path)

        logger.info(
            "[ReflectionAnalysis] Running reflection pass on %d entries.", len(data)
        )
        enriched = self._reflect_results(data)

        self._write_outputs(enriched, output_path)
        return enriched

    # -------------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------------

    def _reflect_results(self, results: list) -> list:
        if self.reflector is None:
            logger.warning(
                "[ReflectionAnalysis] No reflector configured — skipping reflection."
            )
            return results

        enriched = []

        for entry in results:
            enriched_entry = dict(entry)

            # BUG FIX 2: verdict is a string like "INCO; pass; step 2 (C'+T'); ..."
            # There is no "prediction" key.  Use startswith("INCO") to match
            # the format written by JavaTwoStepAnalysis.
            is_inco = entry.get("verdict", "").startswith("INCO")

            if self.only_flagged and not is_inco:
                enriched_entry["reflection"] = None
                enriched.append(enriched_entry)
                continue

            # ── code fields ──────────────────────────────────────────────────
            original_code    = entry.get(self.input_key_code, "")
            # BUG FIX 4: CASCADE writes synthesised code to d["new_code"],
            # not d["synthesized_code"].  Default changed accordingly.
            synthesized_code = entry.get(self.input_key_synth_code, "")

            # synthesized_doc: no standard CASCADE field for this — will be None
            # unless the caller configured a custom input_key_synth_doc that
            # their extraction phase populates.
            synthesized_doc = (
                entry.get(self.input_key_synth_doc)
                if self.input_key_synth_doc else None
            )

            # ── documentation ────────────────────────────────────────────────
            # Try the configured key first, then common fallback names.
            original_doc = (
                entry.get(self.input_key_doc)
                or entry.get("documentation")
                or entry.get("doc", "")
            )

            # ── metrics ──────────────────────────────────────────────────────
            # BUG FIX 5: CASCADE stores d["metric"] = {"p2p": [...], "f2p": [...],
            # "p2f": [...], "f2f": [...]} — lists of test-case name strings.
            # int(entry.get("p2f", 0)) reads a non-existent top-level key.
            metric = entry.get("metric", {})
            p2f    = len(metric.get("p2f", []))
            f2p    = len(metric.get("f2p", []))

            # BUG FIX 6: method name lives at d["signature"]["name"]
            method_name = entry.get("signature", {}).get("name", "<unknown>")

            if not original_code or not synthesized_code:
                logger.warning(
                    "[ReflectionAnalysis] Skipping '%s': missing code fields "
                    "(code=%r, new_code=%r).",
                    method_name,
                    bool(original_code),
                    bool(synthesized_code),
                )
                enriched_entry["reflection"] = {"error": "missing_code_fields"}
                enriched.append(enriched_entry)
                continue

            try:
                # BUG FIX 3: was self._reflector (AttributeError) — correct is self.reflector
                result = self.reflector.reflect(
                    original_code    = original_code,
                    synthesized_code = synthesized_code,
                    original_doc     = original_doc,
                    synthesized_doc  = synthesized_doc,
                    p2f_count        = p2f,
                    f2p_count        = f2p,
                )
                enriched_entry["reflection"] = _result_to_dict(result)
                logger.debug(
                    "[ReflectionAnalysis] '%s' → %s (conf=%.2f)",
                    method_name,
                    result.inconsistency_type,
                    result.precision_confidence,
                )

            except Exception as exc:
                logger.error(
                    "[ReflectionAnalysis] Reflection failed for '%s': %s",
                    method_name, exc,
                    exc_info=True,
                )
                enriched_entry["reflection"] = {"error": str(exc)}

            enriched.append(enriched_entry)

        return enriched

    def _write_outputs(self, enriched: list, output_dir: str) -> None:
        os.makedirs(output_dir, exist_ok=True)

        # reflected.json — full output with reflection sub-dicts
        reflected_path = os.path.join(output_dir, "reflected.json")
        with open(reflected_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)
        logger.info("[ReflectionAnalysis] Wrote %s", reflected_path)

        # Patch inconsistent_functions.json written by the inner analysis
        inco_path = os.path.join(output_dir, "inconsistent_functions.json")
        if os.path.exists(inco_path):
            _enrich_inconsistent_functions(inco_path, enriched)
            logger.info("[ReflectionAnalysis] Patched %s", inco_path)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _result_to_dict(result) -> dict:
    """Serialise a ReflectionResult to a plain dict for JSON output."""
    return {
        "inconsistency_type":   result.inconsistency_type,
        "explanation":          result.explanation,
        "precision_confidence": result.precision_confidence,
        "doc_delta_summary":    result.doc_delta_summary,
        "likely_wrong_side":    result.raw_metadata.get("likely_wrong_side"),
        "escalated_to_llm":     result.raw_metadata.get("escalated_to_llm"),
        "code_diff_line_count": len(result.code_diff_lines),
        "_metadata": {
            k: v for k, v in result.raw_metadata.items()
            if k not in ("escalated_to_llm", "likely_wrong_side")
        },
    }


def _enrich_inconsistent_functions(inco_path: str, enriched: list) -> None:
    """
    Patch reflection results into inconsistent_functions.json.

    Key alignment
    -------------
    JavaTwoStepAnalysis writes inconsistent_functions.json with the key
    "function_name" (from item["signature"]["name"]).

    The enriched list (from the inner analysis) stores the method name at
    entry["signature"]["name"].

    BUG FIX 9: the original code matched on "method_name" (doesn't exist in
    either file) and "id" — neither matched the actual key "function_name".
    """
    with open(inco_path, "r", encoding="utf-8") as f:
        inco_entries = json.load(f)

    # Build lookup: function_name → reflection dict
    reflection_by_fn: dict[str, dict] = {}
    for e in enriched:
        refl = e.get("reflection")
        if not refl:
            continue
        fn_name = e.get("signature", {}).get("name")
        if fn_name:
            reflection_by_fn[fn_name] = refl

    patched = 0
    for entry in inco_entries:
        # inconsistent_functions.json uses "function_name" (see JavaTwoStepAnalysis)
        key = entry.get("function_name")
        if key and key in reflection_by_fn:
            entry["reflection"] = reflection_by_fn[key]
            patched += 1

    with open(inco_path, "w", encoding="utf-8") as f:
        json.dump(inco_entries, f, indent=2, ensure_ascii=False)

    logger.info(
        "[ReflectionAnalysis] Patched %d / %d entries in inconsistent_functions.json",
        patched, len(inco_entries),
    )