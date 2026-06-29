"""
doc_comparator.py
=================

Compares the ``doc`` fields of two Java-method JSON files using an LLM to
detect *semantic* differences in documentation.

Schema of each JSON
-------------------
A list of records, each with:
    {id, doc, signature, language, parent, code, code_file_path,
     called_functions, tests, test_imports, test_file_path}

where ``parent`` contains ``{name, doc, imports, other_methods, variables, generics}``.

What this tool compares (per record)
-------------------------------------
  1. The method's own ``doc``
  2. The parent class ``doc``
  3. Every sibling method's ``doc`` listed in ``parent.other_methods``

Output
------
Same schema as json1 (the original), extended with a ``doc_comparison`` object:

  {
    "matched":   true | false,
    "matched_id": "<id from json2>",
    "original_doc":   "...",
    "generated_doc":  "...",
    "method_doc_diff": {
        "has_semantic_difference": true | false,
        "severity":    "none" | "minor" | "major",
        "explanation": "..."
    },
    "parent_doc_diff": {
        "original_parent_doc":  "...",
        "generated_parent_doc": "...",
        "has_semantic_difference": ..., "severity": ..., "explanation": ...
    },
    "sibling_methods_doc_diffs": [
        {
            "method_name": "subtract",
            "params": ["int a", "int b"],
            "original_doc":  "...",
            "generated_doc": "...",
            "has_semantic_difference": ..., "severity": ..., "explanation": ...
        },
        ...
    ]
  }

Duplicate LLM calls are avoided via an in-process cache keyed on
(context_label, original_doc, generated_doc).

Usage
-----
  python doc_comparator.py original.json generated.json output.json

  # With a vLLM server:
  python doc_comparator.py original.json generated.json output.json \\
      --model Qwen/Qwen3-Coder-30B-A3B-Instruct \\
      --base-url http://localhost:8000/v1

  # Dry-run (skip LLM, useful for testing the matching logic):
  python doc_comparator.py original.json generated.json output.json --dummy

Environment variables
---------------------
  OPENAI_API_KEY  – used when no ``--base-url`` is specified.
  VLLM_API_KEY    – used for vLLM / OpenAI-compatible servers.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import time
from typing import Optional

from openai import OpenAI

# ---------------------------------------------------------------------------
# Base class: try project import first, fall back to a local stub.
# ---------------------------------------------------------------------------
try:
    from cascade.generation.executor.LLMCaller import LLMCaller  # type: ignore
except ImportError:

    class LLMCaller:  # type: ignore
        """Minimal stand-alone base class (used when cascade is not installed)."""

        def execute(self, prompt, **kwargs):
            raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════
# LLM caller  (identical interface to the one supplied by the user)
# ═══════════════════════════════════════════════════════════════════════════


class OpenAICaller(LLMCaller):
    """Thin wrapper around the OpenAI / vLLM chat-completion API."""

    def __init__(
        self,
        max_attempts: int = 3,
        max_tokens: int = 16_000,
        temperature: float = 0.0,
        delay: float = 5.0,
        dummy: bool = False,
        model: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        freq_penalty: float = 0.0,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 86_400.0,
    ):
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay
        self.freq_penalty = freq_penalty
        self.model = model

        if dummy:
            self.client = None
            return

        client_kwargs: dict = {"timeout": timeout}
        if base_url is not None:
            # vLLM or any OpenAI-compatible server
            client_kwargs["base_url"] = base_url
            client_kwargs["api_key"] = os.environ.get(
                "VLLM_API_KEY", api_key or "dummy"
            )
        else:
            client_kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", api_key)

        self.client = OpenAI(**client_kwargs)

    def execute(self, prompt: list[dict], **kwargs):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                request_kwargs: dict = {
                    "model": self.model,
                    "messages": prompt,
                    "frequency_penalty": self.freq_penalty,
                    **kwargs,
                }
                if self.max_tokens is not None:
                    request_kwargs["max_completion_tokens"] = self.max_tokens
                return self.client.chat.completions.create(**request_kwargs)
            except Exception as exc:
                print(f"  Generation attempt {attempt + 1} failed: {exc}")
                attempt += 1
                time.sleep(self.delay)
        raise RuntimeError("Generation failed because of repeated errors.")


# ═══════════════════════════════════════════════════════════════════════════
# Record matching
# ═══════════════════════════════════════════════════════════════════════════


def _record_key(item: dict) -> tuple:
    """Composite key used to pair records across the two JSON files."""
    return (
        item.get("parent", {}).get("name", ""),
        item["signature"]["name"],
        tuple(item["signature"].get("params", [])),
        item.get("code_file_path", ""),
    )


def match_records(
    json1: list[dict], json2: list[dict]
) -> list[tuple[dict, Optional[dict]]]:
    """
    Pair every record in *json1* with its counterpart in *json2*.
    Unmatched json1 entries are paired with ``None``.
    """
    index: dict[tuple, list[dict]] = {}
    for item in json2:
        index.setdefault(_record_key(item), []).append(item)

    return [
        (item, (index.get(_record_key(item)) or [None])[0])
        for item in json1
    ]


# ═══════════════════════════════════════════════════════════════════════════
# LLM prompting
# ═══════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """
You are an expert Java software engineer specialising in documentation quality.

Your task: given two documentation strings for the *same* Java method or class,
decide whether they convey *semantically* different information.

CRITICAL RULES — you MUST follow these exactly:
  • Output ONLY the JSON object below. Nothing before it, nothing after it.
  • Do NOT write any reasoning, explanation, preamble, or markdown outside the JSON.
  • Do NOT use code fences (``` or ```json).

Output schema (fill in the values):
{"has_semantic_difference": <true|false>, "severity": <"none"|"minor"|"major">, "explanation": "<one sentence>"}

Severity guide:
  "none"  – Docs are equivalent; only wording differs.
  "minor" – Small factual omission or extra detail; overall intent is the same.
  "major" – Docs describe different behaviour, contradict each other, or one is
             substantially incomplete / misleading compared to the other.

--- EXAMPLES ---

Context: Method 'add' in class 'Calculator'
Original: "Returns the sum of a and b."
Generated: "Computes the sum of two integer arguments and returns the result."
Output: {"has_semantic_difference": false, "severity": "none", "explanation": "Both descriptions convey addition of two values; only the phrasing differs."}

Context: Method 'subtract' in class 'Calculator'
Original: "Returns the difference a - b."
Generated: "Multiplies two integer values and returns the resulting product."
Output: {"has_semantic_difference": true, "severity": "major", "explanation": "Original describes subtraction; generated describes multiplication — completely different operations."}

Context: Class-level doc for 'Calculator'
Original: ""
Generated: "A utility class for basic arithmetic."
Output: {"has_semantic_difference": true, "severity": "minor", "explanation": "Original is empty; generated adds a description, but introduces no contradiction."}
""".strip()


def _build_llm_prompt(context: str, original: str, generated: str) -> list[dict]:
    user = (
        f"Context: {context}\n\n"
        f"Original documentation:\n\"\"\"\n{original or '(empty)'}\n\"\"\"\n\n"
        f"Generated documentation:\n\"\"\"\n{generated or '(empty)'}\n\"\"\"\n\n"
        "Return the JSON comparison object."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _extract_raw_content(response) -> str:
    """
    Pull the text out of an OpenAI-style chat response.

    Qwen3 (and other thinking models) may deliver the final answer in
    ``message.content`` while the chain-of-thought lives in
    ``message.reasoning_content``.  When the model exhausts its token
    budget *during* thinking, ``content`` can be an empty string even
    though a valid answer was produced.  We therefore:

      1. Use ``content`` if it is non-empty.
      2. Fall back to ``reasoning_content`` (vLLM extended-thinking field).
      3. Raise clearly if both are empty.
    """
    msg = response.choices[0].message
    content = (msg.content or "").strip()
    if content:
        return content

    # Fallback: some vLLM / Qwen3 deployments expose reasoning separately
    reasoning = getattr(msg, "reasoning_content", None) or ""
    if reasoning.strip():
        return reasoning.strip()

    raise ValueError(
        "LLM returned an empty response (both content and reasoning_content are blank). "
        "Consider raising --max-tokens or disabling extended thinking on your server."
    )


def _parse_llm_response(raw: str) -> dict:
    """
    Robustly parse the LLM's JSON response.

    Handles in order:
      1. Qwen3 ``<think>…</think>`` blocks (stripped before parsing).
      2. Markdown ``` / ```json fences.
      3. Direct ``json.loads`` on the cleaned text.
      4. Last-resort regex scan for the first ``{…}`` object in the text,
         in case the model added a prose preamble despite instructions.
    """
    if not raw or not raw.strip():
        raise ValueError("Received an empty string to parse.")

    # 1. Remove <think>...</think> blocks produced by extended-thinking models
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # 2. Strip markdown code fences (```json … ``` or ``` … ```)
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end]).strip()

    if not text:
        raise ValueError("Response was empty after stripping <think> blocks and fences.")

    # 3. Direct parse (happy path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. Scan every {...} block in the text and try each from LAST to FIRST.
    #    When models write prose before answering, the JSON is at the end.
    candidates = list(re.finditer(r"\{[^{}]*\}", text, re.DOTALL))
    for m in reversed(candidates):
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON object found in LLM response: {text[:300]!r}")


# ═══════════════════════════════════════════════════════════════════════════
# DocComparator  (stateful; caches LLM calls)
# ═══════════════════════════════════════════════════════════════════════════


class DocComparator:
    """
    Wraps the LLM caller with caching so that identical (context, doc1, doc2)
    triples are only sent to the model once.
    """

    _DUMMY_RESULT: dict = {
        "has_semantic_difference": None,
        "severity": "unknown",
        "explanation": "Dummy mode — no LLM call made.",
    }

    def __init__(self, caller: OpenAICaller):
        self._caller = caller
        self._cache: dict[tuple, dict] = {}

    # ── Low-level compare ───────────────────────────────────────────────

    def compare(self, context: str, original: str, generated: str) -> dict:
        """
        Ask the LLM whether *original* and *generated* docs are semantically
        different for the element described by *context*.
        Returns a dict with ``has_semantic_difference``, ``severity``,
        ``explanation``.

        Successful results are cached; errors are **not** cached so that a
        transient failure on one record does not permanently poison the result
        for identical (context, original, generated) triples encountered later.
        """
        cache_key = (context, original or "", generated or "")
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Dummy mode: caller.client is None
        if self._caller.client is None:
            result = dict(self._DUMMY_RESULT)
            self._cache[cache_key] = result
            return result

        prompt = _build_llm_prompt(context, original, generated)
        try:
            # response_format=json_object forces the model to output valid JSON
            # and suppresses any prose preamble. Not all models/servers support
            # it, so we fall back to a plain call if it raises an error.
            try:
                response = self._caller.execute(
                    prompt,
                    response_format={"type": "json_object"},
                )
            except Exception:
                response = self._caller.execute(prompt)

            raw = _extract_raw_content(response)
            result = _parse_llm_response(raw)
            # Only cache on success so transient errors don't get locked in
            self._cache[cache_key] = result
        except Exception as exc:
            print(f"  ⚠ LLM error for context '{context}': {exc}")
            result = {
                "has_semantic_difference": None,
                "severity": "unknown",
                "explanation": f"Error during LLM call or JSON parse: {exc}",
            }

        return result

    # ── Convenience: parent class doc ───────────────────────────────────

    def compare_parent_doc(self, item1: dict, item2: Optional[dict]) -> dict:
        parent_name = item1.get("parent", {}).get("name", "unknown")
        orig = item1.get("parent", {}).get("doc", "")
        gen = (item2 or {}).get("parent", {}).get("doc", "")
        diff = self.compare(f"Class-level doc for '{parent_name}'", orig, gen)
        return {
            "original_parent_doc": orig,
            "generated_parent_doc": gen,
            **diff,
        }

    # ── Convenience: sibling method docs ────────────────────────────────

    def compare_sibling_docs(
        self,
        parent_name: str,
        siblings1: list[dict],
        siblings2: list[dict],
    ) -> list[dict]:
        """
        Compare the ``doc`` of each sibling method in *siblings1* with its
        counterpart in *siblings2* (matched by name + params).
        """
        idx2: dict[tuple, dict] = {
            (
                m["signature"]["name"],
                tuple(m["signature"].get("params", [])),
            ): m
            for m in (siblings2 or [])
        }

        results = []
        for m1 in siblings1 or []:
            key = (
                m1["signature"]["name"],
                tuple(m1["signature"].get("params", [])),
            )
            m2 = idx2.get(key)
            orig = m1.get("doc", "")
            gen = (m2 or {}).get("doc", "")
            ctx = (
                f"Sibling method '{m1['signature']['name']}' "
                f"in class '{parent_name}'"
            )
            diff = self.compare(ctx, orig, gen)
            results.append(
                {
                    "method_name": m1["signature"]["name"],
                    "params": m1["signature"].get("params", []),
                    "original_doc": orig,
                    "generated_doc": gen,
                    **diff,
                }
            )
        return results


# ═══════════════════════════════════════════════════════════════════════════
# Per-record comparison
# ═══════════════════════════════════════════════════════════════════════════


def _build_doc_comparison(
    comparator: DocComparator,
    item1: dict,
    item2: Optional[dict],
) -> dict:
    """
    Build the full ``doc_comparison`` sub-object for one matched pair,
    covering method doc, parent class doc, and sibling method docs.
    """
    parent_name = item1.get("parent", {}).get("name", "unknown")
    method_name = item1["signature"]["name"]

    orig_doc = item1.get("doc", "")
    gen_doc = (item2 or {}).get("doc", "")

    method_diff = comparator.compare(
        f"Method '{method_name}' in class '{parent_name}'",
        orig_doc,
        gen_doc,
    )
    parent_diff = comparator.compare_parent_doc(item1, item2)
    sibling_diffs = comparator.compare_sibling_docs(
        parent_name,
        item1.get("parent", {}).get("other_methods", []),
        (item2 or {}).get("parent", {}).get("other_methods", []),
    )

    return {
        "matched": item2 is not None,
        "matched_id": (item2 or {}).get("id"),
        "original_doc": orig_doc,
        "generated_doc": gen_doc,
        "method_doc_diff": method_diff,
        "parent_doc_diff": parent_diff,
        "sibling_methods_doc_diffs": sibling_diffs,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Output builder
# ═══════════════════════════════════════════════════════════════════════════


def build_output(
    pairs: list[tuple[dict, Optional[dict]]],
    comparator: DocComparator,
) -> list[dict]:
    """
    For every (item1, item2) pair, deep-copy item1 (preserving the original
    schema) and attach a ``doc_comparison`` field.
    """
    total = len(pairs)
    width = len(str(total))
    output: list[dict] = []

    for i, (item1, item2) in enumerate(pairs, start=1):
        label = (
            f"{item1.get('parent', {}).get('name', '?')}."
            f"{item1['signature']['name']}"
        )
        status = "✓ matched" if item2 else "✗ unmatched"
        print(f"[{i:{width}}/{total}]  {label}  …  {status}")

        entry = copy.deepcopy(item1)

        if item2 is None:
            entry["doc_comparison"] = {
                "matched": False,
                "error": "No corresponding entry found in the generated JSON.",
            }
        else:
            entry["doc_comparison"] = _build_doc_comparison(
                comparator, item1, item2
            )

        output.append(entry)

    return output


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


def compare_json_files(
    path1: str,
    path2: str,
    output_path: str,
    caller: OpenAICaller,
) -> list[dict]:
    """
    Load *path1* (original) and *path2* (generated), compare their
    documentation fields with the LLM, and write an enriched JSON to
    *output_path*.

    Parameters
    ----------
    path1:       Path to the original JSON file.
    path2:       Path to the LLM-generated JSON file.
    output_path: Destination for the output JSON.
    caller:      A configured ``OpenAICaller`` instance.

    Returns
    -------
    The list of output records (also written to *output_path*).
    """
    with open(path1, encoding="utf-8") as fh:
        json1: list[dict] = json.load(fh)
    with open(path2, encoding="utf-8") as fh:
        json2: list[dict] = json.load(fh)

    print(f"Loaded {len(json1):,} records from '{path1}'")
    print(f"Loaded {len(json2):,} records from '{path2}'\n")

    pairs = match_records(json1, json2)
    n_matched = sum(1 for _, b in pairs if b is not None)
    print(f"Matched {n_matched}/{len(pairs)} records.\n")

    comparator = DocComparator(caller)
    output = build_output(pairs, comparator)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print(f"\nDone. Results written to '{output_path}'")
    _print_summary(output)
    return output


# ═══════════════════════════════════════════════════════════════════════════
# Summary helper
# ═══════════════════════════════════════════════════════════════════════════


def _print_summary(output: list[dict]) -> None:
    """Print a brief statistics table to stdout."""
    severity_counts: dict[str, int] = {"none": 0, "minor": 0, "major": 0, "unknown": 0}
    unmatched = 0

    for entry in output:
        dc = entry.get("doc_comparison", {})
        if not dc.get("matched", True):
            unmatched += 1
            continue
        sev = dc.get("method_doc_diff", {}).get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    print("\n── Method-doc difference summary ──")
    print(f"  No difference (none)  : {severity_counts['none']}")
    print(f"  Minor difference      : {severity_counts['minor']}")
    print(f"  Major difference      : {severity_counts['major']}")
    print(f"  Unknown / error       : {severity_counts.get('unknown', 0)}")
    print(f"  Unmatched records     : {unmatched}")
    print(f"  Total records         : {len(output)}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


OUTPUT_FILENAME = "diff_doc.json"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Compare Java-method documentation across two JSON files using an LLM. "
            f"Results are always written as '{OUTPUT_FILENAME}' inside --output-dir."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("json1", help="Original JSON file (ground truth)")
    p.add_argument("json2", help="Generated JSON file (to compare against)")
    p.add_argument(
        "--output-dir",
        default=".",
        help="Directory where diff_doc.json will be written (default: current directory)",
    )
    p.add_argument(
        "--model",
        default="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        help="LLM model name",
    )
    p.add_argument(
        "--base-url",
        default=None,
        help="vLLM / OpenAI-compatible base URL (omit for OpenAI API)",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="API key; falls back to OPENAI_API_KEY / VLLM_API_KEY env vars",
    )
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="Max tokens per LLM response (raise if the model writes prose before JSON)",
    )
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Seconds to wait between retry attempts",
    )
    p.add_argument(
        "--dummy",
        action="store_true",
        help="Skip LLM calls (useful for testing the matching logic)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    llm = OpenAICaller(
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        max_attempts=args.max_attempts,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        delay=args.delay,
        dummy=args.dummy,
    )
    output_path = os.path.join(args.output_dir, OUTPUT_FILENAME)
    os.makedirs(args.output_dir, exist_ok=True)
    compare_json_files(args.json1, args.json2, output_path, llm)