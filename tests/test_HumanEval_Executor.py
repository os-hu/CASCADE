import unittest
from src.implementations.extraction.HumanEval_Basic_Extraction import HumanEval_Basic_Extraction
from src.implementations.analysis.analysis_executor.HumanEval_Executor import HumanEval_Executor

class test_HumanEval_Executor(unittest.TestCase):

    def test_build_signature(self):
        extractor = HumanEval_Basic_Extraction()
        data = extractor.extract("test_resources/humanevaltest/HumanEval.jsonl.gz", "")

        subj = data[10]
        executor = HumanEval_Executor()
        executor.build_code_file(subj)

        print("\n-------------------------------------------")

        subj = data[10]
        executor = HumanEval_Executor(debug = True)
        executor.build_code_file(subj)

        print("\n-------------------------------------------")

        subj = data[133]
        executor = HumanEval_Executor()
        executor.build_code_file(subj)

    def test_extract_execute_HE(self):
        # extract HE
        extractor = HumanEval_Basic_Extraction()
        data = extractor.extract("test_resources/humanevaltest/HumanEval.jsonl.gz", "")

        amount = 160
        amount = len(data)

        executor = HumanEval_Executor(debug=False)
        for d in data:
            results = executor.execute("code" , "tests", d)
            print(d["id"])
            if not results[0]:
               print("ERROR:" , results)
