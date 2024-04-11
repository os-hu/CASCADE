import unittest
from src.implementations.extraction.Human_Eval_Basic_Extraction import Human_Eval_Basic_Extraction

class test_HE_Extraction(unittest.TestCase):
    """
    for this the follwoing files and folders have to exist:
    TODO fill this
    """
    def test_errors(self):
        extractor = Human_Eval_Basic_Extraction()
        # test wrong path
        with self.assertRaises(FileNotFoundError):
           extractor.extract("./test_resources/humanevaltest/nonexistentpath", "")

        # test more than one file in a directory
        with self.assertRaises(FileNotFoundError):
            extractor.extract("./test_resources/humanevaltest/", "")

        # test wrong file extension
        with self.assertRaises(FileNotFoundError):
            extractor.extract("./test_resources/humanevaltest/humanevaltest/dummy.txt", "")

        # test
        with self.assertRaises(FileNotFoundError):
            extractor.extract("./test_resources/humanevaltest/nonexistentpath", "")

    def test_gz_extraction(self):
        extractor = Human_Eval_Basic_Extraction()
        extractor.extract("./test_resources/humanevaltest/HumanEval.jsonl.gz", "")

    def test_jsonl_extraction(self):
        extractor = Human_Eval_Basic_Extraction()
        extractor.extract("./test_resources/humanevaltest/single_test/humanevaltest.jsonl", "")

    def test_folder_extraction(self):
        extractor = Human_Eval_Basic_Extraction()
        extractor.extract("./test_resources/humanevaltest/single_test/", "")

    def test_extraction(self):
        extractor = Human_Eval_Basic_Extraction()
        data = extractor.extract("test_resources/humanevaltest/HumanEval.jsonl.gz", "")
        self.assertEqual(164 , len(data))

    def test_Test_extraction(self):
        extractor = Human_Eval_Basic_Extraction()
        data = extractor.extract("test_resources/humanevaltest/HumanEval.jsonl.gz", "")
        count = 0
        for d in data:
            if "assert " in d["tests"]:
                count += 1
        self.assertEqual(0, count)



if __name__ == '__main__':
    unittest.main()
