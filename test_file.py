
from src.implementations.generation.code_generator.GPT35_Code_Generator import GPT35_Code_Generator
from src.implementations.generation.test_generator.GPT35_Test_Generator import GPT35_Test_Generator
from src.implementations.generation.prompt_executor.GPT35Completion_Prompt_Executor import GPT35Completion_Prompt_Executor
from src.Generation import Generation

from src.implementations.extraction.HumanEval_Basic_Extraction import HumanEval_Basic_Extraction

from tqdm import tqdm



in_path = "/home/kiecketo/PycharmProjects/CASCADE/tests/test_resources/humanevaltest/single_test/humanevaltest.jsonl"

out_path = "/home/kiecketo/PycharmProjects/CASCADE/resources/output"

api_key_path = "/home/kiecketo/PycharmProjects/CASCADE/api_keys/openai_key"



extractor = HumanEval_Basic_Extraction()
extr = extractor.extract(in_path, out_path, print_mode=True)

print(f"extracted{len(extr)}" )


code_generator = GPT35_Code_Generator(api_key_path)
test_generator = GPT35_Test_Generator(api_key_path)
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

from src.implementations.generation.prompt_executor.GPT35Completion_Prompt_Executor import GPT35Completion_Prompt_Executor

executor = GPT35Completion_Prompt_Executor(api_key_path)
res = executor.generate(prompt)
print(res)


# for c in tqdm(extr):
#     res, res2 = generator.generate_tests(c, ".")
#     print(res)


