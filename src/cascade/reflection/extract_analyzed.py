"""
extract_analyzed.py
-------------------
Given an analyzed.json (or a list of them), classifies every code item as
"original" or "synthesized" and surfaces the associated documentation.

Classification rules
--------------------
CODE  → always ORIGINAL  (every `code` field holds a real implementation)
DOC   → ORIGINAL   if the JavaDoc contains meaningful content
        SYNTHESIZED if it is an empty stub (/** */) or absent

Usage
-----
    python extract_analyzed.py analyzed.json
    python extract_analyzed.py analyzed.json --output report.json
    python extract_analyzed.py analyzed.json --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CodeItem:
    item_type: str            # "class" | "main_method" | "other_method"
    class_name: str
    name: str
    language: str
    file_path: str

    # ── doc ──
    doc: str
    doc_status: str           # "original" | "synthesized"

    # ── code ──
    code: Optional[str]       # None for class-level items
    code_status: str = "original"   # always original per spec

    # ── extra ──
    signature: dict = field(default_factory=dict)
    modifiers: list[str] = field(default_factory=list)
    returns: Optional[str] = None
    params: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Doc classification
# ---------------------------------------------------------------------------

_SYNTHESIZED_DOC_BODIES = {
    "",
    "/**\n */",
    "/**\n */\n",
    "/***/",
    "/** */",
}


def _classify_doc(doc: str) -> str:
    """Return 'synthesized' if *doc* is an empty JavaDoc stub, 'original' otherwise."""
    if doc is None:
        return "synthesized"
    normalized = doc.strip()
    if normalized in _SYNTHESIZED_DOC_BODIES:
        return "synthesized"
    # Also catch stubs whose only content is whitespace / * lines with no text
    inner = (
        normalized
        .replace("/**", "")
        .replace("*/", "")
        .replace("*", "")
        .strip()
    )
    return "synthesized" if not inner else "original"


# ---------------------------------------------------------------------------
# Extraction logic
# ---------------------------------------------------------------------------

def _sig_dict(sig: dict) -> dict:
    """Return a compact, serialisable representation of a method signature."""
    return {
        "name":       sig.get("name", ""),
        "returns":    sig.get("returns", ""),
        "params":     sig.get("params", []),
        "modifiers":  sig.get("modifier", []),
        "exceptions": sig.get("exceptions", []),
        "annotations":sig.get("annotations", []),
    }


def extract_items(entry: dict) -> list[CodeItem]:
    """Extract all CodeItem objects from a single JSON entry."""
    items: list[CodeItem] = []

    language  = entry.get("language", "unknown")
    file_path = entry.get("code_file_path", "")
    parent    = entry.get("parent", {})
    class_name = parent.get("name", "unknown")

    # ── 1. Parent class ───────────────────────────────────────────────────
    class_doc = parent.get("doc", "")
    items.append(CodeItem(
        item_type  = "class",
        class_name = class_name,
        name       = class_name,
        language   = language,
        file_path  = file_path,
        doc        = class_doc,
        doc_status = _classify_doc(class_doc),
        code       = None,
        signature  = {},
    ))

    # ── 2. Main (focal) method ────────────────────────────────────────────
    sig        = entry.get("signature", {})
    method_doc = entry.get("doc", "")
    method_code= entry.get("code", "")
    items.append(CodeItem(
        item_type  = "main_method",
        class_name = class_name,
        name       = sig.get("name", "unknown"),
        language   = language,
        file_path  = file_path,
        doc        = method_doc,
        doc_status = _classify_doc(method_doc),
        code       = method_code,
        signature  = _sig_dict(sig),
        returns    = sig.get("returns"),
        params     = sig.get("params", []),
        exceptions = sig.get("exceptions", []),
        modifiers  = sig.get("modifier", []),
    ))

    # ── 3. Other methods in parent ────────────────────────────────────────
    for m in parent.get("other_methods", []):
        m_sig  = m.get("signature", {})
        m_doc  = m.get("doc", "")
        m_code = m.get("code", "")
        items.append(CodeItem(
            item_type  = "other_method",
            class_name = class_name,
            name       = m_sig.get("name", "unknown"),
            language   = language,
            file_path  = file_path,
            doc        = m_doc,
            doc_status = _classify_doc(m_doc),
            code       = m_code,
            signature  = _sig_dict(m_sig),
            returns    = m_sig.get("returns"),
            params     = m_sig.get("params", []),
            exceptions = m_sig.get("exceptions", []),
            modifiers  = m_sig.get("modifier", []),
        ))

    return items


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

_DIVIDER  = "=" * 68
_DIVIDER2 = "-" * 68


def _render_item(item: CodeItem, verbose: bool) -> str:
    lines: list[str] = [_DIVIDER]
    lines.append(f"  TYPE      : {item.item_type.replace('_', ' ').upper()}")
    lines.append(f"  CLASS     : {item.class_name}")
    lines.append(f"  NAME      : {item.name}")
    lines.append(f"  LANGUAGE  : {item.language}")
    lines.append(f"  FILE      : {item.file_path}")

    if item.signature:
        lines.append(f"  SIGNATURE : {item.signature.get('modifiers', [])} "
                     f"{item.signature.get('returns', '')} "
                     f"{item.name}({', '.join(item.params)})")

    # doc
    doc_label = f"[{item.doc_status.upper()}]"
    lines.append(_DIVIDER2)
    lines.append(f"  DOC  {doc_label}")
    if verbose or item.doc_status == "original":
        for ln in (item.doc or "(none)").strip().splitlines():
            lines.append(f"      {ln}")
    else:
        lines.append("      (empty stub — not shown)")

    # code
    lines.append(_DIVIDER2)
    lines.append(f"  CODE [ORIGINAL]")
    if item.code:
        if verbose:
            for ln in item.code.strip().splitlines():
                lines.append(f"      {ln}")
        else:
            preview = item.code.strip().splitlines()
            for ln in preview[:5]:
                lines.append(f"      {ln}")
            if len(preview) > 5:
                lines.append(f"      … ({len(preview) - 5} more lines)")
    else:
        lines.append("      (class-level — no code body)")

    return "\n".join(lines)


def print_report(items: list[CodeItem], verbose: bool) -> None:
    # Summary counts
    orig_docs  = sum(1 for i in items if i.doc_status == "original")
    synth_docs = sum(1 for i in items if i.doc_status == "synthesized")
    orig_code  = sum(1 for i in items if i.code is not None)

    print("\n" + _DIVIDER)
    print("  ANALYSIS SUMMARY")
    print(_DIVIDER)
    print(f"  Total items  : {len(items)}")
    print(f"  Docs         : {orig_docs} original  /  {synth_docs} synthesized")
    print(f"  Code bodies  : {orig_code} original  (code is always original)")
    print(_DIVIDER)

    for item in items:
        print(_render_item(item, verbose=verbose))

    print(_DIVIDER + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else [data]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract original vs synthesized code/docs from analyzed.json"
    )
    parser.add_argument("input", help="Path to analyzed.json")
    parser.add_argument(
        "--output", "-o",
        help="Optional path to write a structured JSON report",
        default=None,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full code bodies and docs (default: abbreviated)",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"[error] File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    entries = load_json(args.input)
    all_items: list[CodeItem] = []
    for entry in entries:
        all_items.extend(extract_items(entry))

    print_report(all_items, verbose=args.verbose)

    if args.output:
        report = [asdict(item) for item in all_items]
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"[info] JSON report written to: {args.output}")


if __name__ == "__main__":
    main()