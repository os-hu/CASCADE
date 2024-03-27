import unittest
from src.implementations.extraction.Human_Eval_Basic_Extraction import Human_Eval_Basic_Extraction

class MyTestCase(unittest.TestCase):
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




if __name__ == '__main__':
    unittest.main()
