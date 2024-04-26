
from generation.code.GPT35CodeGenerator import Gpt35CodeGenerator
from generation.test.GPT35TestGenerator import Gpt35TestGenerator
from generation.Generation import Generation

from extraction.HumanEvalExtraction import HumanEvalExtraction

in_path = "/home/kiecketo/PycharmProjects/CASCADE/tests/test_resources/humanevaltest/single_test/humanevaltest.jsonl"

out_path = "/test_resources/humanevaltest/output"

api_key_path = "/test_resources/api_keys/openai_key"



extractor = HumanEvalExtraction()
extr = extractor.extract(in_path, out_path, print_mode=True)

print(f"extracted{len(extr)}" )


code_generator = Gpt35CodeGenerator(api_key_path)
test_generator = Gpt35TestGenerator(api_key_path)
generator = Generation(code_generator, test_generator)



prompt = """# SETUP: Write python unittests for this function.

def triangle_area(a, b, c):
    \"\"\"
    Given the lengths of the three sides of a triangle. Return the area of
    the triangle rounded to 2 decimal points if the three sides form a valid triangle. 
    Otherwise return -1
    Three sides make a valid triangle when the sum of any two sides is greater 
    than the third side.
    \"\"\"
    pass

# Tests:
import unittest

class test_Class(unittest.TestCase):"""

from src.implementations.generation.executor.GPT35Completion_Prompt_Executor import GPT35Completion_Prompt_Executor

executor = GPT35Completion_Prompt_Executor(api_key_path)
res = executor.execute(prompt)
print(res)


# for c in tqdm(extr):
#     res, res2 = generator.generate_tests(c, ".")
#     print(res)





# TODO USE THAT IN FILTER
result = filter(lambda x: all([filter(x) for filter in filterList]), data)