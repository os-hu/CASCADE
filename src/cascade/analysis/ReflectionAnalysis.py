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
          "code_generator": {
            "name": "JavaCodeGenerator",
            "kwargs": { "model": "gpt-4.1-mini", "temperature": 0.2 }
          },
          "test_generator": {
            "name": "MultiStepJavaTestGenerator",
            "kwargs": { "model": "gpt-4.1-mini", "temperature": 0.4 }
          }
        }
      },
      "reflector": {
        "name": "ChainedReflector",
        "kwargs": {
          "escalation_threshold": 0.65,
          "llm_kwargs": { "model": "gpt-4.1-mini" }
        }
      },
      "only_flagged": true
    }
  }
}

How the inner_analysis is loaded
---------------------------------
PipelineFactory already uses dynamic class loading by name.  We replicate
that pattern here so this class is self-contained and doesn't import
JavaTwoStepAnalysis directly (keeping language-independence intact).
"""

import importlib
import json
import logging
import os
from typing import Optional

from ..reflection.Reflector import InconsistencyType, ReflectionResult, Reflector

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.executor.ExecutionResults import ExecutionResults

from cascade.generation.Generation import Generation
from cascade.utils.Utils import save_dicts_list_to_json, load_json_from_path
from cascade.utils.JavaUtils import build_signature

from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
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
    # bare import
    module = importlib.import_module(name)
    return getattr(module, name)


def _build_inner_analysis(cfg: dict):
    """Instantiate the inner Analysis from a {name, kwargs} dict."""
    name   = cfg["name"]
    kwargs = cfg.get("kwargs", {})
    cls = _load_class(name, [
        "cascade.analysis",
        "src.cascade.analysis",
    ])
    return cls(**kwargs)


def _build_reflector(cfg: dict) -> Reflector:
    """Instantiate a Reflector from a {name, kwargs} dict."""
    name   = cfg["name"]
    kwargs = cfg.get("kwargs", {})
    cls = _load_class(name, [
        "cascade.reflection",
        "reflection",
    ])
    return cls(**kwargs)


# ---------------------------------------------------------------------------
# ReflectionAnalysis
# ---------------------------------------------------------------------------

class ReflectionAnalysis(Analysis):
    """
    Wraps any CASCADE Analysis and appends a reflection pass on flagged items.

    The class intentionally does NOT inherit from a CASCADE-internal Analysis
    base so that it can be used even when the cascade package is installed as
    a wheel (where internal base classes may not be directly importable).
    PipelineFactory loads it by name through the normal config mechanism.

    Parameters
    ----------
    inner_analysis : dict
        {name, kwargs} config for the wrapped Analysis.
    reflector : dict
        {name, kwargs} config for the Reflector to use.
    only_flagged : bool
        Apply reflection only to INCO-labelled methods (default True).
    input_key_code : str
        analyzed.json key holding the original method body.
    input_key_synth_code : str
        analyzed.json key holding the synthesized implementation (C').
    input_key_doc : str
        analyzed.json key holding the original Javadoc.
    input_key_synth_doc : str
        analyzed.json key holding the synthesized doc (optional).
    """

    def __init__(
        self,
        inner_analysis: dict,
        reflector: dict,
        only_flagged: bool = True,
        input_key_code: str = "code",
        input_key_synth_code: str = "synthesized_code",
        input_key_doc: str = "doc",
        input_key_synth_doc: str = "synthesized_doc",
        **kwargs,
    ):
        self._inner    = _build_inner_analysis(inner_analysis)
        self._reflector = _build_reflector(reflector)
        self.only_flagged         = only_flagged
        self.input_key_code       = input_key_code
        self.input_key_synth_code = input_key_synth_code
        self.input_key_doc        = input_key_doc
        self.input_key_synth_doc  = input_key_synth_doc

    # ------------------------------------------------------------------
    # CASCADE Analysis protocol
    # ------------------------------------------------------------------

    def analyze(self, items: list, output_dir: str) -> list:
        """
        Run the inner analysis, then immediately attach reflection results.

        Parameters
        ----------
        items : list[dict]
            Filtered, extracted method entries from CASCADE's extraction phase.
        output_dir : str
            Directory CASCADE passes for writing output artefacts.

        Returns
        -------
        list[dict]
            Same as inner analysis output but each INCO entry gains a
            "reflection" sub-dict.
        """
        # Step 1 — delegate to the wrapped analysis (generates C', tests, etc.)
        logger.info("[ReflectionAnalysis] Running inner analysis: %s", type(self._inner).__name__)
        results = self._inner.analyze(items, output_dir)

        # Step 2 — reflect on the results in-memory
        logger.info("[ReflectionAnalysis] Running reflection pass on %d entries.", len(results))
        enriched = self._reflect_results(results)

        # Step 3 — write reflected.json and patch inconsistent_functions.json
        self._write_outputs(enriched, output_dir)

        return enriched

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _reflect_results(self, results: list) -> list:
        enriched = []
        flagged_count = sum(1 for r in results if r.get("prediction") == "INCO")
        logger.info("[ReflectionAnalysis] %d INCO entries to reflect on.", flagged_count)

        for entry in results:
            enriched_entry = dict(entry)

            if self.only_flagged and entry.get("prediction") != "INCO":
                enriched_entry["reflection"] = None
                enriched.append(enriched_entry)
                continue

            original_code    = entry.get(self.input_key_code, "")
            synthesized_code = entry.get(self.input_key_synth_code, "")
            original_doc     = entry.get(self.input_key_doc, "")
            synthesized_doc  = entry.get(self.input_key_synth_doc)
            p2f              = int(entry.get("p2f", 0))
            f2p              = int(entry.get("f2p", 0))

            if not original_code or not synthesized_code:
                logger.warning(
                    "[ReflectionAnalysis] Skipping '%s': missing code fields.",
                    entry.get("method_name", "<unknown>"),
                )
                enriched_entry["reflection"] = {"error": "missing_code_fields"}
                enriched.append(enriched_entry)
                continue

            try:
                result: ReflectionResult = self._reflector.reflect(
                    original_code=original_code,
                    synthesized_code=synthesized_code,
                    original_doc=original_doc,
                    synthesized_doc=synthesized_doc,
                    p2f_count=p2f,
                    f2p_count=f2p,
                )
                enriched_entry["reflection"] = _result_to_dict(result)
                logger.debug(
                    "[ReflectionAnalysis] '%s' → %s (conf=%.2f)",
                    entry.get("method_name", "<unknown>"),
                    result.inconsistency_type,
                    result.precision_confidence,
                )
            except Exception as exc:
                logger.error(
                    "[ReflectionAnalysis] Reflection failed for '%s': %s",
                    entry.get("method_name", "<unknown>"),
                    exc,
                    exc_info=True,
                )
                enriched_entry["reflection"] = {"error": str(exc)}

            enriched.append(enriched_entry)

        return enriched

    def _write_outputs(self, enriched: list, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        # reflected.json — full output
        reflected_path = os.path.join(output_dir, "reflected.json")
        with open(reflected_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)
        logger.info("[ReflectionAnalysis] Wrote %s", reflected_path)

        # Patch inconsistent_functions.json if the inner analysis wrote it
        inco_path = os.path.join(output_dir, "inconsistent_functions.json")
        if os.path.exists(inco_path):
            _enrich_inconsistent_functions(inco_path, enriched)
            logger.info("[ReflectionAnalysis] Patched %s", inco_path)


# ---------------------------------------------------------------------------
# Module-level helpers (also used by ReflectionPipeline)
# ---------------------------------------------------------------------------

def _result_to_dict(result: ReflectionResult) -> dict:
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


def _enrich_inconsistent_functions(inco_path: str, enriched: list):
    with open(inco_path, "r", encoding="utf-8") as f:
        inco_entries = json.load(f)

    reflection_by_id = {
        (e.get("method_name") or e.get("id")): e["reflection"]
        for e in enriched
        if e.get("reflection") and (e.get("method_name") or e.get("id"))
    }

    for entry in inco_entries:
        key = entry.get("method_name") or entry.get("id")
        if key in reflection_by_id:
            entry["reflection"] = reflection_by_id[key]

    with open(inco_path, "w", encoding="utf-8") as f:
        json.dump(inco_entries, f, indent=2, ensure_ascii=False)