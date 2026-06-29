import argparse
import json
import re
import uuid
from pathlib import Path

from cascade.generation.Generator import Generator
from cascade.generation.executor.OpenAICaller import OpenAICaller


SYSTEM_PROMPT = """\
You are a Java documentation expert. Analyse the Java source file provided and \
produce a JSON documentation catalogue — completely ignoring any existing JavaDoc \
or inline comments already present in the code.

Return ONLY a valid JSON object with this exact schema (no markdown, no prose):

{
  "file": "<filename>",
  "package": "<package name or null>",
  "imports": ["<import statement>", ...],
  "types": [
    {
      "kind":        "<class|interface|enum|annotation|record>",
      "name":        "<SimpleName>",
      "qualified":   "<fully.qualified.Name>",
      "modifiers":   ["public", ...],
      "synth_description": "<fresh description written by you>",
      "extends":     "<SuperClass or null>",
      "implements":  ["<Interface>", ...],
      "fields": [
        {
          "name":        "<fieldName>",
          "type":        "<JavaType>",
          "modifiers":   ["private", ...],
          "synth_description": "<fresh description>"
        }
      ],
      "constructors": [
        {
          "name":        "<ClassName>",
          "modifiers":   ["public", ...],
          "parameters":  [{"name": "<p>", "type": "<T>"}],
          "throws":      ["<ExceptionType>", ...],
          "synth_description": "<fresh description>"
        }
      ],
      "methods": [
        {
          "name":        "<methodName>",
          "modifiers":   ["public", ...],
          "return_type": "<ReturnType>",
          "parameters":  [{"name": "<p>", "type": "<T>"}],
          "throws":      ["<ExceptionType>", ...],
          "synth_description": "<fresh description>"
        }
      ],
      "enum_constants": [
        { "name": "<CONSTANT>", "synth_description": "<fresh description>" }
      ],
      "nested_types": []
    }
  ]
}

Rules:
- Write every description yourself from scratch; ignore any existing comments.
- enum_constants and nested_types may be empty arrays when not applicable.
- All arrays must be present even if empty.
- Return nothing but the JSON object.
"""

USER_PROMPT_TEMPLATE = """\
Document this Java file. File name: {filename}

{source_code}
"""


class JavaDocGenerator(Generator):
    """
    Walks a Java source tree, strips existing documentation, asks an LLM to
    produce fresh documentation for every type / method / field, and writes
    one flat JSON record **per method / constructor** matching the canonical
    Extraction schema used by JavaDocExtractor.
    """

    def __init__(self, caller: OpenAICaller = None, encoding: str = "utf-8"):
        super().__init__()
        self.caller = caller or OpenAICaller()
        self.encoding = encoding

    # ------------------------------------------------------------------
    # Generator contract
    # ------------------------------------------------------------------

    def generate(self, context, input_path: str, output_path: str):
        """
        Process all .java files under input_path and write a consolidated
        javadoc.json into output_path.  Each entry in the JSON array is one
        method/constructor record matching the Extraction schema.

        :param context: Pipeline context (passed through, not used internally).
        :param input_path: Root directory or single .java file to document.
        :param output_path: Directory that will receive javadoc.json.
        :return: Path to the written JSON file, or None if no sources were found.
        """
        input_path  = Path(input_path)
        output_path = Path(output_path)

        java_files = (
            [input_path]
            if input_path.is_file() and input_path.suffix == ".java"
            else list(input_path.rglob("*.java"))
        )

        if not java_files:
            print(f"[JavaDocGenerator] No .java files found under '{input_path}'.")
            return None

        all_records = []
        for java_file in java_files:
            print(f"[JavaDocGenerator] processing  {java_file} …")
            records = self._document_file(java_file, input_path)
            all_records.extend(records)
            print(f"[JavaDocGenerator] ✓  {len(records)} method record(s) from {java_file.name}")

        output_path.mkdir(parents=True, exist_ok=True)
        out_file = output_path / "javadoc.json"
        out_file.write_text(
            json.dumps(all_records, indent=2, ensure_ascii=False),
            encoding=self.encoding,
        )
        print(f"[JavaDocGenerator] JSON written → {out_file}  ({len(all_records)} total records)")
        return str(out_file)

    # ------------------------------------------------------------------
    # Per-file helpers
    # ------------------------------------------------------------------

    def _document_file(self, java_file: Path, root: Path) -> list[dict]:
        """
        Strip existing JavaDoc from java_file, call the LLM, then flatten
        the LLM output into one Extraction-schema record per method/constructor.

        :param java_file: Path to the Java source file.
        :param root: Project root used to compute relative code_file_path.
        :return: List of per-method extraction dicts.
        """
        raw_source   = java_file.read_text(encoding=self.encoding)
        clean_source = self._strip_javadoc(raw_source)

        prompt      = self._build_prompt(java_file.name, clean_source)
        response    = self.caller.execute(prompt)
        llm_doc     = self._parse_response(response, java_file.name)

        # If the LLM response failed to parse, return a single error sentinel
        if "parse_error" in llm_doc:
            return [llm_doc]

        relative_path = str(java_file.relative_to(root)) if java_file.is_relative_to(root) else java_file.name
        return self._flatten_to_records(llm_doc, relative_path)

    def _flatten_to_records(self, llm_doc: dict, relative_path: str) -> list[dict]:
        """
        Convert the LLM's per-file JSON output into a flat list of per-method
        records that match the Extraction schema.

        Each record has:
          doc            – synth_description written by the LLM
          id             – fresh UUID
          signature      – name / returns / params / modifier / annotations / generics
          language       – "java"
          parent         – qualified type name, imports, sibling methods, fields
          code           – empty string (generator has no source body)
          code_file_path – relative path to the source file
          called_functions – empty list (not available without parsing)
          tests / test_imports / test_file_path – empty (not available here)

        :param llm_doc: Parsed LLM response dict.
        :param relative_path: Source file path relative to the project root.
        :return: Flat list of extraction-schema dicts.
        """
        records = []
        imports = llm_doc.get("imports", [])

        for type_info in llm_doc.get("types", []):
            qualified   = type_info.get("qualified", type_info.get("name", ""))
            type_doc    = type_info.get("synth_description", "")
            modifiers   = type_info.get("modifiers", [])
            fields      = type_info.get("fields", [])
            field_vars  = [f"{f.get('type', '')} {f.get('name', '')}" for f in fields]

            # Collect every method + constructor so we can build the sibling list
            all_callables = self._collect_callables(type_info)

            for item in all_callables:
                sibling_methods = [
                    {
                        "doc":       s["doc"],
                        "signature": s["signature"],
                        "code":      "",
                    }
                    for s in all_callables
                    if s["signature"]["name"] != item["signature"]["name"]
                ]

                record = {
                    "doc":      item["doc"],
                    "id":       str(uuid.uuid4()),
                    "signature": item["signature"],
                    "language": "java",
                    "parent": {
                        "name":          qualified,
                        "doc":           type_doc,
                        "imports":       imports,
                        "other_methods": sibling_methods,
                        "variables":     field_vars,
                        "generics":      [],
                    },
                    "code":             "",
                    "code_file_path":   relative_path,
                    "called_functions": [],
                    "tests":            "",
                    "test_imports":     [],
                    "test_file_path":   "",
                }
                records.append(record)

        return records

    @staticmethod
    def _collect_callables(type_info: dict) -> list[dict]:
        """
        Turn the LLM's constructors + methods lists into intermediate dicts
        with doc + signature keys ready for embedding in extraction records.

        :param type_info: One element from llm_doc["types"].
        :return: List of intermediate callable dicts.
        """
        callables = []

        for ctor in type_info.get("constructors", []):
            params = [
                f"{p.get('type', '')} {p.get('name', '')}".strip()
                for p in ctor.get("parameters", [])
            ]
            callables.append({
                "doc": ctor.get("synth_description", ""),
                "signature": {
                    "name":        ctor.get("name", ""),
                    "returns":     "void",          # constructors have no return type
                    "params":      params,
                    "modifier":    ctor.get("modifiers", []),
                    "annotations": [],
                    "generics":    [],
                },
            })

        for method in type_info.get("methods", []):
            params = [
                f"{p.get('type', '')} {p.get('name', '')}".strip()
                for p in method.get("parameters", [])
            ]
            callables.append({
                "doc": method.get("synth_description", ""),
                "signature": {
                    "name":        method.get("name", ""),
                    "returns":     method.get("return_type", "void"),
                    "params":      params,
                    "modifier":    method.get("modifiers", []),
                    "annotations": [],
                    "generics":    [],
                },
            })

        return callables

    # ------------------------------------------------------------------
    # Prompt & response
    # ------------------------------------------------------------------

    def _build_prompt(self, filename: str, source_code: str) -> list[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    filename=filename,
                    source_code=source_code,
                ),
            },
        ]

    @staticmethod
    def _parse_response(response, filename: str) -> dict:
        raw: str = response.choices[0].message.content.strip()
        fenced = re.fullmatch(r"```(?:json)?\n?(.*?)```", raw, re.DOTALL)
        if fenced:
            raw = fenced.group(1).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"[JavaDocGenerator] WARNING: JSON parse failed for {filename}: {exc}")
            return {"file": filename, "parse_error": str(exc), "raw": raw}

    @staticmethod
    def _strip_javadoc(source: str) -> str:
        source = re.sub(r"/\*\*.*?\*/", "", source, flags=re.DOTALL)
        source = re.sub(r"/\*.*?\*/",   "", source, flags=re.DOTALL)
        source = re.sub(r"//[^\n]*",    "", source)
        source = re.sub(r"\n{3,}", "\n\n", source)
        return source.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a JSON documentation catalogue for a Java project."
    )
    parser.add_argument("--input",    required=True, help="Input directory or single .java file")
    parser.add_argument("--output",   required=True, help="Output directory (receives javadoc.json)")
    parser.add_argument("--model",    default="Qwen/Qwen3-Coder-30B-A3B-Instruct")
    parser.add_argument("--base-url", default=None,  help="vLLM base URL (optional)")
    args = parser.parse_args()

    caller = OpenAICaller(
        model=args.model,
        base_url=args.base_url,
        max_tokens=16000,
        temperature=0,
        max_attempts=3,
        delay=5,
    )

    generator = JavaDocGenerator(caller=caller)

    out = generator.generate(
        context=None,
        input_path=args.input,
        output_path=args.output,
    )
    print(f"\nDone → {out}" if out else "\nNo files processed.")
