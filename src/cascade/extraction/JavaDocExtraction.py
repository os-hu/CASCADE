"""
JavaDocExtractor
================
Implements :class:`Extraction` for Java source files.

For every method / constructor found in a ``.java`` file it extracts:
  - the **original** JavaDoc comment (``doc``)
  - a fully-typed ``signature`` block
  - parent-class context (imports, fields, sibling methods)
  - raw method body (``code``)
  - test-file information when a matching test class is found

The output follows the canonical ``Extraction`` schema so it can be
compared directly against the LLM-generated docs produced by
:class:`JavaDocGenerator`.
"""

import json
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Base class (as provided)
# ---------------------------------------------------------------------------

class Extraction(ABC):
    @abstractmethod
    def extract(self, input_path, output_path) -> List[dict]:
        pass


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Matches a single /** ... */ JavaDoc block (non-greedy)
_JAVADOC_RE = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)

# Strips leading * from JavaDoc lines
_STAR_STRIP_RE = re.compile(r"^\s*\*\s?", re.MULTILINE)

# Captures @param / @return / @throws tags inside a JavaDoc block
_TAG_RE = re.compile(r"@(\w+)\s+(.*?)(?=@\w+|\Z)", re.DOTALL)

# import statements
_IMPORT_RE = re.compile(r"^\s*import\s+([\w.*]+);", re.MULTILINE)

# package declaration
_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+);", re.MULTILINE)

# Top-level / nested class|interface|enum|record declaration
_TYPE_RE = re.compile(
    r"(?P<javadoc>/\*\*.*?\*/\s*)?"
    r"(?P<modifiers>(?:(?:public|protected|private|static|abstract|final|sealed|non-sealed)\s+)*)"
    r"(?P<kind>class|interface|enum|record)\s+(?P<name>\w+)"
    r"(?:<[^{]*>)?"                        # optional generics
    r"(?:\s+extends\s+(?P<extends>[\w.<>, ]+?))?"
    r"(?:\s+implements\s+(?P<implements>[\w.<>, ]+?))?"
    r"\s*\{",
    re.DOTALL,
)

# Field declaration (simplified — covers the common cases)
_FIELD_RE = re.compile(
    r"(?:/\*\*(?P<doc>.*?)\*/\s*)?"
    r"(?P<modifiers>(?:(?:public|protected|private|static|final|volatile|transient)\s+)+)"
    r"(?P<type>[\w.<>\[\]]+)\s+(?P<name>\w+)\s*(?:=.*?)?;",
    re.DOTALL,
)

# Method / constructor declaration
_METHOD_RE = re.compile(
    r"(?P<javadoc>/\*\*(?P<doc>.*?)\*/\s*)?"
    r"(?P<annotations>(?:@\w+(?:\([^)]*\))?\s*)*)"
    r"(?P<modifiers>(?:(?:public|protected|private|static|abstract|final|synchronized|native|default|override)\s+)*)"
    r"(?:(?P<generics><[^(]*?>)\s+)?"
    r"(?P<return_type>[\w.<>\[\]?]+)\s+"
    r"(?P<name>\w+)\s*"
    r"\((?P<params>[^)]*)\)"
    r"(?:\s+throws\s+(?P<throws>[\w.,\s<>]+?))?"
    r"\s*(?P<body>\{)",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Low-level parse helpers
# ---------------------------------------------------------------------------

def _clean_javadoc(raw: str) -> str:
    """Strip ``*`` leaders and leading/trailing whitespace from a raw JavaDoc body."""
    return _STAR_STRIP_RE.sub("", raw).strip()


def _parse_params(params_str: str) -> List[str]:
    """
    Convert a raw parameter string like ``"int x, String name"``
    into ``["int x", "String name"]``.
    """
    params_str = params_str.strip()
    if not params_str:
        return []
    # Split on commas but respect generic angle-brackets
    result, depth, current = [], 0, ""
    for ch in params_str:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            result.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        result.append(current.strip())
    return result


def _extract_body(source: str, brace_pos: int) -> str:
    """
    Given *source* and the position of the opening ``{``, return the complete
    method body (including braces) by counting brace depth.
    """
    depth, start = 0, brace_pos
    for i, ch in enumerate(source[brace_pos:], start=brace_pos):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    return source[start:]


def _find_test_file(java_file: Path, root: Path) -> Optional[Path]:
    """
    Heuristically locate a JUnit test file for *java_file*.
    Looks for ``<ClassName>Test.java`` or ``Test<ClassName>.java`` anywhere under *root*.
    """
    stem = java_file.stem
    candidates = [f"{stem}Test.java", f"Test{stem}.java"]
    for candidate in candidates:
        hits = list(root.rglob(candidate))
        if hits:
            return hits[0]
    return None


# ---------------------------------------------------------------------------
# Main Extractor
# ---------------------------------------------------------------------------

class JavaDocExtractor(Extraction):
    """
    Extracts original JavaDoc and structural metadata from Java source files,
    producing one record per *method / constructor* that matches the canonical
    ``Extraction`` schema.

    The ``doc`` field contains the **original** JavaDoc comment so it can be
    compared directly with the LLM-generated documentation from
    :class:`JavaDocGenerator`.
    """

    def __init__(self, encoding: str = "utf-8"):
        """
        :param encoding: Character encoding used when reading source files.
        """
        self.encoding = encoding

    # ------------------------------------------------------------------
    # Extraction contract
    # ------------------------------------------------------------------

    def extract(self, input_path: str, output_path: str) -> List[dict]:
        """
        Walk *input_path* recursively, extract every method / constructor from
        every ``.java`` file, and write the results to ``extracted.json`` under
        *output_path*.

        :param input_path: Root directory or single ``.java`` file.
        :param output_path: Directory that will receive ``extracted.json``.
                            If *output_path* ends with ``.json`` the file is
                            written directly to that path.
        :return: List of extracted method dicts (one per method / constructor).
        """
        input_path  = Path(input_path)
        output_path = Path(output_path)

        java_files = (
            [input_path]
            if input_path.is_file() and input_path.suffix == ".java"
            else list(input_path.rglob("*.java"))
        )

        # Exclude test files from the main extraction pass
        java_files = [f for f in java_files if not self._is_test_file(f)]

        if not java_files:
            print(f"[JavaDocExtractor] No .java source files found under '{input_path}'.")
            return []

        root = input_path if input_path.is_dir() else input_path.parent
        records: List[dict] = []

        for java_file in java_files:
            print(f"[JavaDocExtractor] extracting  {java_file} …")
            file_records = self._extract_file(java_file, root)
            records.extend(file_records)
            print(f"[JavaDocExtractor] ✓  {len(file_records)} method(s) from {java_file.name}")

        # Determine output file path
        if output_path.suffix == ".json":
            out_file = output_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            out_file = output_path / "doc_extracted.json"

        # Append to existing file if present
        existing: List[dict] = []
        if out_file.exists():
            try:
                existing = json.loads(out_file.read_text(encoding=self.encoding))
            except json.JSONDecodeError:
                pass

        combined = existing + records
        out_file.write_text(
            json.dumps(combined, indent=2, ensure_ascii=False),
            encoding=self.encoding,
        )
        print(f"[JavaDocExtractor] extracted.json written → {out_file}  ({len(combined)} total records)")
        return records

    # ------------------------------------------------------------------
    # Per-file extraction
    # ------------------------------------------------------------------

    def _extract_file(self, java_file: Path, root: Path) -> List[dict]:
        """
        Parse a single Java source file and return one extraction dict
        per method / constructor.

        :param java_file: Path to the ``.java`` file.
        :param root: Project root used to compute relative paths.
        :return: List of extraction dicts.
        """
        source = java_file.read_text(encoding=self.encoding)
        relative_path = str(java_file.relative_to(root))

        package   = self._extract_package(source)
        imports   = self._extract_imports(source)
        test_file = _find_test_file(java_file, root)
        test_source, test_imports, test_path = self._load_test_file(test_file, root)

        records: List[dict] = []

        for type_match in _TYPE_RE.finditer(source):
            type_name  = type_match.group("name")
            type_kind  = type_match.group("kind")
            type_mods  = type_match.group("modifiers").split() if type_match.group("modifiers") else []
            type_doc   = ""
            if type_match.group("javadoc"):
                raw = _JAVADOC_RE.search(type_match.group("javadoc"))
                if raw:
                    type_doc = _clean_javadoc(raw.group(1))

            qualified = f"{package}.{type_name}" if package else type_name
            fields    = self._extract_fields(source)

            # Collect all methods in this type for the "other_methods" sibling list
            all_methods = self._extract_methods(source, java_file.name)

            for method in all_methods:
                sibling_methods = [
                    {
                        "doc":       m["doc"],
                        "signature": m["signature"],
                        "code":      m["code"],
                    }
                    for m in all_methods
                    if m["signature"]["name"] != method["signature"]["name"]
                ]

                record = {
                    "doc": method["doc"],
                    "id":  str(uuid.uuid4()),
                    "signature": method["signature"],
                    "language": "java",
                    "parent": {
                        "name":         qualified,
                        "doc":          type_doc,
                        "imports":      imports,
                        "other_methods": sibling_methods,
                        "variables":    [f["type"] + " " + f["name"] for f in fields],
                        "generics":     [],
                    },
                    "code":            method["code"],
                    "code_file_path":  relative_path,
                    "called_functions": self._find_called_functions(method["code"]),
                    "tests":           test_source,
                    "test_imports":    test_imports,
                    "test_file_path":  test_path,
                }
                records.append(record)

        return records

    # ------------------------------------------------------------------
    # Parse helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_package(source: str) -> str:
        m = _PACKAGE_RE.search(source)
        return m.group(1) if m else ""

    @staticmethod
    def _extract_imports(source: str) -> List[str]:
        return [f"import {m.group(1)};" for m in _IMPORT_RE.finditer(source)]

    @staticmethod
    def _extract_fields(source: str) -> List[dict]:
        fields = []
        for m in _FIELD_RE.finditer(source):
            fields.append({
                "name":      m.group("name"),
                "type":      m.group("type"),
                "modifiers": m.group("modifiers").split(),
                "doc":       _clean_javadoc(m.group("doc")) if m.group("doc") else "",
            })
        return fields

    @staticmethod
    def _extract_methods(source: str, filename: str) -> List[dict]:
        """
        Extract every method / constructor from *source* and return a list of
        intermediate dicts ready to be embedded in an extraction record.
        """
        methods = []
        for m in _METHOD_RE.finditer(source):
            name        = m.group("name")
            return_type = m.group("return_type")
            params_raw  = m.group("params") or ""
            throws_raw  = m.group("throws") or ""
            mods_raw    = m.group("modifiers") or ""
            generics    = [m.group("generics").strip("<>")] if m.group("generics") else []
            annotations = re.findall(r"@\w+", m.group("annotations") or "")

            # Skip obvious non-methods (e.g. 'if', 'while', 'for' captured by regex)
            if name in {"if", "while", "for", "switch", "catch", "try", "else"}:
                continue

            # Extract raw JavaDoc text
            raw_doc = ""
            if m.group("doc"):
                raw_doc = _clean_javadoc(m.group("doc"))

            # Find the method body
            brace_pos = m.start("body")
            body = _extract_body(source, brace_pos)

            params = _parse_params(params_raw)
            throws = [t.strip() for t in throws_raw.split(",") if t.strip()]

            methods.append({
                "doc": raw_doc,
                "code": body,
                "signature": {
                    "name":        name,
                    "returns":     return_type,
                    "params":      params,
                    "modifier":    mods_raw.split(),
                    "annotations": annotations,
                    "generics":    generics,
                },
            })
        return methods

    @staticmethod
    def _find_called_functions(body: str) -> List[str]:
        """
        Extract method call expressions from *body* using a simple regex.
        Returns strings like ``"obj.method(arg1, arg2)"``.
        """
        return re.findall(r"\b(\w+\.\w+\s*\([^)]*\)|\w+\s*\([^)]*\))", body)

    def _load_test_file(
        self, test_file: Optional[Path], root: Path
    ):
        """
        Read a test file and return (content, imports, relative_path).
        Returns empty strings / lists when no test file is found.
        """
        if test_file is None:
            return "", [], ""
        try:
            content = test_file.read_text(encoding=self.encoding)
            imports = [f"import {m.group(1)};" for m in _IMPORT_RE.finditer(content)]
            return content, imports, str(test_file.relative_to(root))
        except Exception:
            return "", [], ""

    @staticmethod
    def _is_test_file(java_file: Path) -> bool:
        """Return *True* for files that look like JUnit test classes."""
        name = java_file.stem
        return name.endswith("Test") or name.startswith("Test")
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract JavaDoc from a Java project.")
    parser.add_argument("--input",  required=True, help="Input directory or single .java file")
    parser.add_argument("--output", required=True, help="Output directory (receives doc_extracted.json)")
    args = parser.parse_args()

    extractor = JavaDocExtractor()
    extractor.extract(args.input, args.output)