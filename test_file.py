from src.Pipeline import Pipeline
from src.extraction.HumanEvalExtraction import HumanEvalExtraction
from src.extraction.JavaExtraction import JavaExtraction
from src.filters.CheckLengthFilterFunction import CheckLengthFilterFunction
from src.filters.ContainsFilterFunction import ContainsFilterFunction
from src.filters.Filter import Filter
from src.analysis.TreeAnalysis import TreeAnalysis
from src.filters.NoTestsFilterFunction import NoTestsFilterFunction

from src.generation.Generation import Generation
from src.generation.code.GPT35CodeGenerator import GPT35CodeGenerator
from src.generation.code.GPT35JavaCodeGenerator import GPT35JavaCodeGenerator
from src.generation.test.GPT35TestGenerator import GPT35TestGenerator
from src.generation.test.GPT4TestGenerator import GPT4TestGenerator

from src.generation.NoGenerator import NoGenerator

from src.analysis.executor.HumanEvalExecutor import HumanEvalExecutor
from src.analysis.visualizer.TreeVisualizer import TreeVisualizer

# test pipeline

in_path = "/home/kiecketo/repos/commons-text"
out_path = "./temp/"

extraction = JavaExtraction()
filter_ = Filter([
    NoTestsFilterFunction(),
    ContainsFilterFunction(key="doc", content="@inheritDoc", invert=True),
    CheckLengthFilterFunction(key="doc", op=">", val=10),
    # CheckLengthFilterFunction(key="doc", op="<", val=400)
])

debug = True

code_generator = GPT35JavaCodeGenerator(max_attempts=3, dummy=True)

data = extraction.extract(in_path, out_path)

data = filter_.filter_all(data, out_path)

length = []
for d in data:
    length.append(len(code_generator.build_prompt(d)))
    #print(code_generator.build_prompt(d))

print(sorted(length))

#test_generator = GPT35JavaTestGenerator(max_attempts=3)
#
# generator = Generation(code_generator, test_generator, NoGenerator())
# executor = HumanEvalExecutor()
# visualizer = TreeVisualizer()
#
# analysis = TreeAnalysis(generator, executor, visualizer, debug=debug)
#
# setup = {}
#
# pipeline = Pipeline(extraction, filter_, analysis, setup)
#
# results = pipeline.execute(in_path, out_path)

# DATA = extraction.extract("./tests/resources/humanevaltest/output/analyzed.json", out_path)
# visualizer.visualize(DATA, full=True)
