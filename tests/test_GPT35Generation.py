import unittest
from src.extraction.HumanEvalExtraction import HumanEvalExtraction

class test_GPT35Generation(unittest.TestCase):
    def setUp(self):
        self.context = HumanEvalExtraction().extract(
            "resources/humanevaltest/datasets/single_test/humanevaltest.jsonl", "")

    def test_prompt_builder(self):
        # TODO
        pass