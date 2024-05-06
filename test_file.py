from src.Pipeline import Pipeline
from src.extraction.HumanEvalExtraction import HumanEvalExtraction
from src.filters.Filter import Filter
from src.analysis.TreeAnalysis import TreeAnalysis

from src.generation.Generation import Generation
from src.generation.code.GPT35CodeGenerator import GPT35CodeGenerator
from src.generation.test.GPT35TestGenerator import GPT35TestGenerator
from src.generation.test.GPT4TestGenerator import GPT4TestGenerator

from src.generation.NoGenerator import NoGenerator

from src.analysis.executor.HumanEvalExecutor import HumanEvalExecutor
from src.analysis.visualizer.TreeVisualizer import TreeVisualizer

# test pipeline

in_path = "./tests/resources/humanevaltest/datasets/HumanEval.jsonl.gz"
out_path = "./tests/resources/humanevaltest/output/he4"


extraction = HumanEvalExtraction()
#filter_ = Filter([lambda x: 122 < int(x["id"]) < 126 ])
filter_ = Filter([])

api_key_path = "./tests/resources/apikeys/openai_key"
code_gen_args = {}

debug = True

code_generator = GPT35CodeGenerator(api_key_path, max_attempts=3)
test_generator = GPT4TestGenerator(api_key_path, max_attempts=3)

generator = Generation(code_generator, test_generator, NoGenerator())
executor = HumanEvalExecutor()
visualizer = TreeVisualizer()


analysis = TreeAnalysis(generator, executor, visualizer, debug=debug)

setup = {}

pipeline = Pipeline(extraction, filter_, analysis, setup)

results = pipeline.execute(in_path, out_path)


#DATA = extraction.extract("./tests/resources/humanevaltest/output/analyzed.json", out_path)
#visualizer.visualize(DATA, full=True)


