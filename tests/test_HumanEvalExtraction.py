import shutil
import unittest
from cascade.extraction.HumanEvalExtraction import HumanEvalExtraction

class test_HumanEvalExtraction(unittest.TestCase):
    """
    for this the follwoing files and folders have to exist:
    TODO fill this
    """
    def test_errors(self):
        extractor = HumanEvalExtraction()
        # test wrong path
        with self.assertRaises(FileNotFoundError):
            extractor.extract("./resources/humanevaltest/nonexistentpath", "resources/he")

        # test more than one file in a directory

        # test wrong file extension
        with self.assertRaises(FileNotFoundError):
            extractor.extract("./resources/humanevaltest/datasets/dummy.txt", "resources/he")

    def test_gz_extraction(self):
        extractor = HumanEvalExtraction()
        extractor.extract("./resources/humanevaltest/datasets/HumanEval.jsonl.gz", "resources/he")
        shutil.rmtree("resources/he")

    def test_jsonl_extraction(self):
        extractor = HumanEvalExtraction()
        extractor.extract("./resources/humanevaltest/datasets/single_test/humanevaltest.jsonl", "resources/he")
        shutil.rmtree("resources/he")

    def test_folder_extraction(self):
        extractor = HumanEvalExtraction()
        extractor.extract("./resources/humanevaltest/datasets/single_test/", "resources/he")
        shutil.rmtree("resources/he")

    def test_extraction(self):
        extractor = HumanEvalExtraction()
        data = extractor.extract("resources/humanevaltest/datasets/HumanEval.jsonl.gz", "resources/he")
        self.assertEqual(164 , len(data))
        shutil.rmtree("resources/he")

    def test_Test_extraction(self):
        extractor = HumanEvalExtraction()
        data = extractor.extract("resources/humanevaltest/datasets/HumanEval.jsonl.gz", "resources/he")
        count = 0
        for d in data:
            if "assert " in d["tests"]:
                count += 1
        self.assertEqual(0, count)
        shutil.rmtree("resources/he")
