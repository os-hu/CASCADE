# exampleTargetproject

This folder contains a tiny Java project and ready-to-run CASCADE configs.

## Project content

- `repository/src/main/java/example/Calculator.java`
  - `add(int a, int b)`: documentation and implementation are consistent.
  - `subtract(int a, int b)`: documentation says subtraction, but implementation multiplies (intentional inconsistency).
- `repository/src/test/java/example/CalculatorTest.java`
- `repository/pom.xml`

## Configs

- `dataset.json`: smoke test config (extraction + empty analysis, no OpenAI required).
- `gpt4o_maven.json`: full CASCADE flow with generation and Maven executor (OpenAI + Docker required).

## Quick run commands

From repository root:

```bash
PYTHONPATH=src python -m cascade.CLI run -i "./exampleTargetproject/repository" -o "./exampleTargetproject" -s "./exampleTargetproject/dataset.json"
```

If CASCADE is installed as a CLI tool:

```bash
./cascade.venv/bin/CASCADE run -i "./exampleTargetproject/repository" -o "./exampleTargetproject" -s "./exampleTargetproject/dataset.json"
```

Full LLM run:

```bash
./cascade.venv/bin/CASCADE run -i "./exampleTargetproject/repository" -o "./exampleTargetproject" -s "./exampleTargetproject/gpt4o_maven.json" -ana debug:3
```

## Output files

- `extracted.json`: extracted functions and metadata.
- `analyzed.json`: analysis output and generated artifacts.
- `log.txt`, `errors.txt` (depending on selected analysis).

