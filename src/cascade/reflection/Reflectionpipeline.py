"""
reflection/ReflectionPipeline.py
---------------------------------
Wires the Reflector into CASCADE's post-analysis phase.

Usage
-----
This class is instantiated by the PipelineFactory from your config file,
exactly like any other CASCADE component:

    {
      "reflection": {
        "name": "ReflectionPipeline",
        "kwargs": {
          "reflector_name": "ChainedReflector",
          "reflector_kwargs": {
            "escalation_threshold": 0.65,
            "llm_kwargs": { "model": "gpt-4.1-mini" }
          },
          "only_flagged": true
        }
      }
    }

Input
-----
Reads `analyzed.json` produced by CASCADE's two-step analysis.
Each entry is expected to have at minimum:
  - "code"              : str   — original method body
  - "doc"               : str   — original Javadoc
  - "synthesized_code"  : str   — CASCADE's generated C'
  - "prediction"        : str   — "INCO" | "NoInco"
  - "p2f"               : int
  - "f2p"               : int

Optional fields consumed when present:
  - "synthesized_doc"   : str   — doc generated from C' (if a DocGenerator ran)

Output
------
Writes `reflected.json` alongside `analyzed.json`.
Each entry is the original dict plus a "reflection" sub-object:
  {
    ...original fields...,
    "reflection": {
      "inconsistency_type": "...",
      "explanation": "...",
      "precision_confidence": 0.82,
      "doc_delta_summary": "...",
      "likely_wrong_side": "code",
      "escalated_to_llm": true
    }
  }

Also updates `inconsistent_functions.json` in-place, adding the "reflection"
block to each already-flagged entry so downstream consumers get enriched data.
"""

import importlib
import json
import logging
import os
from typing import Optional

from .Reflector import ReflectionResult, Reflector

logger = logging.getLogger(__name__)


def _load_reflector(name: str, kwargs: dict) -> Reflector:
    """
    Mirrors PipelineFactory's dynamic class loading convention.
    Looks in `reflection` package first; falls back to absolute import.
    """
    try:
        module = importlib.import_module(f"cascade.reflection.{name}")
    except ModuleNotFoundError:
        module = importlib.import_module(name)
    cls = getattr(module, name)
    return cls(**kwargs)


class ReflectionPipeline:
    """
    Post-analysis pipeline step that enriches CASCADE's output with
    structured inconsistency reflection.

    Parameters
    ----------
    reflector_name : str
        Class name of the Reflector to instantiate (must be in the
        `reflection` package or on the module path).
    reflector_kwargs : dict
        Constructor kwargs forwarded to the Reflector.
    only_flagged : bool
        If True (default), only reflect on methods already labelled INCO.
        Set to False to run reflection on all methods (useful for research).
    input_key_code : str
        Key in the analyzed.json entry that holds the original code.
    input_key_synth_code : str
        Key for the synthesized code.
    input_key_doc : str
        Key for the original documentation.
    input_key_synth_doc : str
        Key for the synthesized documentation (may be absent).
    """

    def __init__(
        self,
        reflector_name: str = "ChainedReflector",
        reflector_kwargs: Optional[dict] = None,
        only_flagged: bool = True,
        input_key_code: str = "code",
        input_key_synth_code: str = "synthesized_code",
        input_key_doc: str = "doc",
        input_key_synth_doc: str = "synthesized_doc",
        **kwargs,
    ):
        self.only_flagged = only_flagged
        self.input_key_code = input_key_code
        self.input_key_synth_code = input_key_synth_code
        self.input_key_doc = input_key_doc
        self.input_key_synth_doc = input_key_synth_doc
        self._reflector = _load_reflector(reflector_name, reflector_kwargs or {})

    # ------------------------------------------------------------------

    def run(self, analyzed_path: str, output_dir: str) -> str:
        """
        Process analyzed.json and write reflected.json.

        Parameters
        ----------
        analyzed_path : str
            Path to CASCADE's `analyzed.json`.
        output_dir : str
            Directory where `reflected.json` will be written.

        Returns
        -------
        str
            Path to the written `reflected.json`.
        """
        with open(analyzed_path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        reflected_entries = []
        for entry in entries:
            reflected_entry = dict(entry)

            prediction = entry.get("prediction", "")
            if self.only_flagged and prediction != "INCO":
                reflected_entry["reflection"] = None
                reflected_entries.append(reflected_entry)
                continue

            original_code    = entry.get(self.input_key_code, "")
            synthesized_code = entry.get(self.input_key_synth_code, "")
            original_doc     = entry.get(self.input_key_doc, "")
            synthesized_doc  = entry.get(self.input_key_synth_doc)
            p2f              = int(entry.get("p2f", 0))
            f2p              = int(entry.get("f2p", 0))

            if not original_code or not synthesized_code:
                logger.warning(
                    "Skipping reflection for entry '%s': missing code fields.",
                    entry.get("method_name", "<unknown>"),
                )
                reflected_entry["reflection"] = {"error": "missing_code_fields"}
                reflected_entries.append(reflected_entry)
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
                reflected_entry["reflection"] = self._result_to_dict(result)
            except Exception as exc:
                logger.error(
                    "Reflection failed for '%s': %s",
                    entry.get("method_name", "<unknown>"),
                    exc,
                    exc_info=True,
                )
                reflected_entry["reflection"] = {"error": str(exc)}

            reflected_entries.append(reflected_entry)

        # Write reflected.json
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "reflected.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(reflected_entries, f, indent=2, ensure_ascii=False)

        logger.info("Reflection complete. Results written to %s", out_path)

        # Also enrich inconsistent_functions.json if it exists
        inco_path = os.path.join(output_dir, "inconsistent_functions.json")
        if os.path.exists(inco_path):
            self._enrich_inconsistent_functions(inco_path, reflected_entries)

        return out_path

    # ------------------------------------------------------------------

    @staticmethod
    def _result_to_dict(result: ReflectionResult) -> dict:
        return {
            "inconsistency_type":   result.inconsistency_type,
            "explanation":          result.explanation,
            "precision_confidence": result.precision_confidence,
            "doc_delta_summary":    result.doc_delta_summary,
            "likely_wrong_side":    result.raw_metadata.get("likely_wrong_side"),
            "escalated_to_llm":     result.raw_metadata.get("escalated_to_llm"),
            # Keep diff lines in a compact form for the JSON
            "code_diff_line_count": len(result.code_diff_lines),
            "_metadata":            {
                k: v for k, v in result.raw_metadata.items()
                if k not in ("escalated_to_llm", "likely_wrong_side")
            },
        }

    @staticmethod
    def _enrich_inconsistent_functions(inco_path: str, reflected_entries: list):
        """Patch reflection blocks into inconsistent_functions.json in-place."""
        with open(inco_path, "r", encoding="utf-8") as f:
            inco_entries = json.load(f)

        # Build lookup: method identifier → reflection block
        reflection_by_id = {}
        for entry in reflected_entries:
            key = entry.get("method_name") or entry.get("id")
            if key and entry.get("reflection"):
                reflection_by_id[key] = entry["reflection"]

        for entry in inco_entries:
            key = entry.get("method_name") or entry.get("id")
            if key in reflection_by_id:
                entry["reflection"] = reflection_by_id[key]

        with open(inco_path, "w", encoding="utf-8") as f:
            json.dump(inco_entries, f, indent=2, ensure_ascii=False)

        logger.info("Enriched %s with reflection data.", inco_path)