import unittest
from src.implementations.generation.prompt_executor.GPT35Completion_Prompt_Executor import GPT35Completion_Prompt_Executor
from src.implementations.generation.code_generator.GPT35_Code_Generator import GPT35_Code_Generator
from src.implementations.generation.test_generator.GPT35_Test_Generator import GPT35_Test_Generator
from src.implementations.extraction.HumanEval_Basic_Extraction import HumanEval_Basic_Extraction

class test_GPT35_Genearotrs(unittest.TestCase):
    def setUp(self):
        self.context = HumanEval_Basic_Extraction().extract("./test_resources/humanevaltest/single_test/humanevaltest.jsonl", "")

    def test_prompt_builder(self):
        # TODO
        pass