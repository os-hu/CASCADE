This repository contains **CASCADE** (our code-comment inconsistency detection and test-generation tool) 
together with the full benchmark we used to evaluate it in our Paper. 

The code is organized so that you can either **re-run the complete benchmark end-to-end** or 
**inspect the pre-computed results** shipped with the paper.

The tool itself is build around expandability, so that you can easily add new validation approaches to the benchmark 
(e.g., by adding a new sub‑folder in `drivers/` and implementing the necessary code to run it on the dataset).
It can be adapted for new languages and for different analyses.

furthermore it contains the novel inconsistency dataset we curated for our evaluation, 
which is available in `paperEvaluation/dataset.zip`.

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
├─ configs/                 # Configuration files for the differetn CASCADE pipelines
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
