from src.Pipeline import Pipeline
from src.extraction.HumanEvalExtraction import HumanEvalExtraction
from src.filters.Filter import Filter
from src.analysis.TreeAnalysis import TreeAnalysis

from src.generation.Generation import Generation
from src.generation.code.GPT35CodeGenerator import GPT35CodeGenerator
from src.generation.test.GPT35TestGenerator import GPT35TestGenerator
from src.generation.NoGenerator import NoGenerator

from src.analysis.executor.HumanEvalExecutor import HumanEvalExecutor
from src.analysis.visualizer.TreeVisualizer import TreeVisualizer

# test pipeline

in_path = "./tests/resources/humanevaltest/datasets/single_test/humanevaltest.jsonl"
out_path = "./tests/resources/temp"


extraction = HumanEvalExtraction()
filter_ = Filter([])


api_key_path = "./tests/resources/apikeys/openai_key"
code_gen_args = {}


code_generator = GPT35CodeGenerator(api_key_path, **code_gen_args)
test_generator = GPT35TestGenerator(api_key_path)

generator = Generation(code_generator, test_generator, NoGenerator())
executor = HumanEvalExecutor()
visualizer = TreeVisualizer()


analysis = TreeAnalysis(generator, executor, visualizer)

setup = {}

pipeline = Pipeline(extraction, filter_, analysis, setup)

results = pipeline.execute(in_path, out_path)
