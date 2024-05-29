from src.Pipeline import Pipeline
from src.extraction.HumanEvalExtraction import HumanEvalExtraction
from src.extraction.HumanEvalIncoExtraction import HumanEvalIncoExtraction
from src.extraction.JavaExtraction import JavaExtraction
from src.extraction.JsonExtraction import JsonExtraction
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



in_path = "/home/kiecketo/repos/HE/HumanEvalInco.json"
out_path = ""


json_extr = HumanEvalIncoExtraction()

data = json_extr.extract(in_path, out_path)

print(GPT4TestGenerator(dummy=True).build_prompt(data[10]))

