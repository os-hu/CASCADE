"""
Example: run JavaDocGenerator on a Java project and produce javadoc.json.

Usage:
    python example_usage.py --input ./my-java-project --output ./docs

Environment variables:
    OPENAI_API_KEY   – standard OpenAI key
    VLLM_API_KEY     – key for a local vLLM-compatible server
"""

import argparse
from cascade.generation.executor.OpenAICaller import OpenAICaller
from cascade.generation.doc.JavaDocGenerator import JavaDocGenerator


def main():
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


if __name__ == "__main__":
    main()