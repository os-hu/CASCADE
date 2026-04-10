## 1 Overview

This repository contains **CASCADE** (our code-comment inconsistency detection and test-generation tool) 
together with the full benchmark we used to evaluate it in our Paper. (folder: `PaperEvaluation`)

The tool itself is build around expandability, so that you can easily add new validation approaches to the benchmark
Or adapt it for new languages and for different analyses.


If you want to run the benchmark from scratch, you can follow the instructions in `PaperEvaluation/README.md`

If you want to try out CASCADE on your own projects, you can follow the instructions in section 4.

An example Java project you can try it on is described in Section 6.



---

## 2  Repository layout

```
.
├─ paperEvaluation/
│  ├─ dataset.zip           # Evaluation dataset (see Section 3 for details)
│  ├─ drivers/              # One sub‑folder per validation approach (see Section 4 for details)
│  │   ├─ DocChecker/
│  │   ├─ Baseline/
│  │   └─ CASCADE/
│  ├─ run.sh                # dataset execution file (runs all drivers on the dataset)
│  ├─ eval.py               # Computes & prints all benchmark metrics
│  └─ results_RQ1.zip       # Pre‑computed experiment results
├─ datasetExtraction/       # scripts we used to extract the original dataset
├─ configs/                 # Configuration files for different CASCADE pipelines
└─ src/                     # Source code of the CASCADE tool


````

## 3  `src/` directory structure

The main implementation lives in `src/cascade/`, which contains the code that wires the CASCADE pipeline together.

- `Pipeline.py` and `PipelineFactory.py` orchestrate the end-to-end workflow and build pipeline instances from configuration.
- `CLI.py` provides the command-line entry point, and `build.py` contains build/helper logic used by the project.
- `analysis/` contains the analysis layer, including the abstractions and concrete analysis implementations.
- `extraction/` contains the extraction layer, which reads input projects or datasets and produces structured data.
- `filters/` contains filtering logic used to discard items that do not meet the desired criteria.
- `generation/` contains code, test, and documentation generators, grouped into `code/`, `test/`, and `doc/` subfolders.
- `utils/` contains shared helper functions and utilities used across the project.
- `resources/` stores bundled assets such as external tools and other project resources.


## 4  Running CASCADE

CASCADE can be built and run as a standalone tool.

### 4.1 Install

Create a virtual environment:

```bash
python3 -m venv cascade.venv
```

If you are inside the main CASCADE folder (on one level with src and setup.py) install it with:

```bash
./cascade.venv/bin/pip install .
```

CASCADE requires an OpenAI key in the environment. 
Even if you do not plan to use LLM-based analysis, the key is still required for some of the generators, 
which are used in some of the analyses use "dummy" as a key then

```bash
export OPENAI_API_KEY=<your key>
```

### 4.2 Run command format

General command:

```bash
./cascade.venv/bin/CASCADE run -i "<input-project-root>" -o "<output-folder>" -s "<config.json>"
```

you can use CLI overrides replace values in the config file kwargs at runtime.

ie to change the temperature of the llm for the code geneartor use:

```bash
./cascade.venv/bin/CASCADE run -i "<input-project-root>" -o "<output-folder>" -s "<config.json>" --code-generator temperature:0.7
```


## 5 Expanding CASCADE

CASCADE is designed to be extended. You can add custom extraction logic, filters, generators, analyses, and executors
without changing the core pipeline orchestration.

The easiest way to extend it is:

1. inherit from the matching abstract base class,
2. follow one existing implementation as a template,
3. reference your class in the config file (`name` + `kwargs`).

Common extension points and examples:

- **Analysis**: inherit from `src/cascade/analysis/Analysis.py` (example: `JavaTwoStepAnalysis.py`)
- **FilterFunction**: inherit from `src/cascade/filters/FilterFunction.py` (example: `ContainsFilterFunction.py`, `CheckLengthFilterFunction.py`)
- **Generators**: inherit from `src/cascade/generation/Generator.py` in `code/`, `test/`, or `doc/`
  (example: `JavaCodeGenerator.py`, `GPT4JavaTestGenerator.py`)
- **Executor**: inherit from `src/cascade/analysis/executor/AnalysisExecutor.py`
  (example: `MavenJavaExecutor.py`, `JavaExecutor.py`)

Minimal config example:

```json
{
  "Extraction": { "name": "JavaExtraction", "kwargs": {} },
  "Analysis": { "name": "EmptyAnalysis", "kwargs": {} },
  "Executor": { "name": "MavenJavaExecutor", "kwargs": {} }
}
```

If your custom classes are outside `src/cascade`, pass their location with CLI `--module-path`.
`PipelineFactory` loads classes dynamically from the names in your config file.

If you build a cool or useful extension, feel free to open a pull request.


## 6  Example project

A tiny runnable example is included in `exampleTargetproject/`.

It contains one Java class with two functions:

- `add(int a, int b)`: doc and implementation are consistent.
- `subtract(int a, int b)`: doc says subtraction, implementation multiplies (intentional inconsistency).

Files:

- `exampleTargetproject/repository/src/main/java/example/Calculator.java`
- `exampleTargetproject/repository/src/test/java/example/CalculatorTest.java`
- `exampleTargetproject/repository/pom.xml`
- `exampleTargetproject/dataset.json`

### 6.1 Run the tiny workflow

From repository root:

```bash
cd ./exampleTargetproject
../cascade.venv/bin/CASCADE run -i "./repository" -o "." -s "./dataset.json"
```

Equivalent single command from root:

```bash
./cascade.venv/bin/CASCADE run -i "./exampleTargetproject/repository" -o "./exampleTargetproject" -s "./exampleTargetproject/dataset.json"
```

### 6.2 What to inspect after running

- `exampleTargetproject/extracted.json`: extracted method-level context from the Java project.
- `exampleTargetproject/analyzed.json`: output from the configured analysis step.

The example config uses `EmptyAnalysis` so it is a lightweight end-to-end smoke test of extraction/filtering/pipeline wiring.
For full inconsistency detection with generation and execution, switch to a config that uses LLM generators and a non-empty analysis strategy.

