

TODO  READ AND CORRECT THIS




# CASCADE Driver README

This folder contains the CASCADE driver used in the paper evaluation run.

## What this driver does

`driver.sh` runs CASCADE with:

- input repository folder (`-i`)
- output folder (`-o`)
- pipeline config JSON (`-s`)
- optional CLI overrides (for example `-ana debug:3`)

Current command in `driver.sh`:

```zsh
../../../../../../../cascade.venv/bin/CASCADE run -i "./repository" -o "." -s "./dataset.json" -ana debug:3
```

## Quick start

From the repository root (`/home/kiecketo/PycharmProjects/CASCADE`):

```zsh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Then run CASCADE directly:

```zsh
CASCADE run -i "./PaperEvaluation/drivers/CASCADE/repository" -o "./PaperEvaluation/drivers/CASCADE" -s "./PaperEvaluation/drivers/CASCADE/dataset.json" -ana debug:3
```

Or run the paper driver script from its folder:

```zsh
cd /home/kiecketo/PycharmProjects/CASCADE/PaperEvaluation/drivers/CASCADE
bash driver.sh
```

## Running on a whole project/repository

Set `-i` to the root directory of the Java project/repository you want to analyze.

For `JavaExtraction`, this should usually be a project root that contains both source and test code in the normal Java layout.

Example:

```zsh
CASCADE run -i "./repository" -o "." -s "./dataset.json" -ana debug:3
```

## How the config file works (`-s`)

The config JSON defines which components are instantiated by `PipelineFactory`.

Main sections:

- `Extraction`
- `CodeGenerator` (optional)
- `TestGenerator` (optional)
- `DocGenerator` (optional)
- `Analysis`
- `Executor`
- `FilterFunctions` (optional list)

Each section uses:

- `name`: class name to load
- `kwargs`: constructor keyword arguments

Example shape:

```json
{
  "Extraction": { "name": "JavaExtraction", "kwargs": {} },
  "CodeGenerator": { "name": "JavaCodeGenerator", "kwargs": { "model": "gpt-4o-mini-2024-07-18" } },
  "TestGenerator": { "name": "MultiStepJavaTestGenerator", "kwargs": { "model": "gpt-4o-mini-2024-07-18", "temperature": 0.7 } },
  "Analysis": { "name": "DatasetAnalysis", "kwargs": {} },
  "Executor": { "name": "MavenJavaExecutor", "kwargs": {} }
}
```

## CLI overrides (override config `kwargs`)

You can override component kwargs from the command line.

Format:

- regular components: `key:value`
- filters: `(index,key:value)`

Supported override flags:

- `-extr` / `--extraction`
- `-codegen` / `--code-generator`
- `-testgen` / `--test-generator`
- `-docgen` / `--doc-generator`
- `-ana` / `--analysis`
- `-exec` / `--executor`
- `-filter` / `--filters`

Examples:

```zsh
CASCADE run -i "./repository" -o "." -s "./dataset.json" -ana debug:3
CASCADE run -i "./repository" -o "." -s "./dataset.json" -testgen temperature:0.3
CASCADE run -i "./repository" -o "." -s "./dataset.json" -filter "(1,invert:True)"
```

Override precedence: values from CLI override the matching values in config `kwargs`.

## Useful options

- `-m` / `--module-path`: add path for user-defined modules/classes.
- `--debug-cli`: print parsed override kwargs before pipeline build.

## Output

CASCADE writes intermediate and analysis artifacts to `-o` (output path), including files like `extracted.json` and `analyzed.json` depending on pipeline configuration and run state.

