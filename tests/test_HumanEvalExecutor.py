import os
import shutil
import unittest
from cascade.extraction.HumanEvalExtraction import HumanEvalExtraction
from cascade.analysis.executor.HumanEvalExecutor import HumanEvalExecutor


class test_HumanEvalExecutor(unittest.TestCase):
    def test_build_signature(self):
        extractor = HumanEvalExtraction()
        data = extractor.extract("resources/humanevaltest/datasets/HumanEval.jsonl.gz", "resources/he/")

        subj = data[10]
        executor = HumanEvalExecutor()
        executor.build_code_file(subj)

        subj = data[10]
        executor = HumanEvalExecutor(debug=True)
        executor.build_code_file(subj)

        subj = data[133]
        executor = HumanEvalExecutor()
        executor.build_code_file(subj)
        # TODO buidl some asserts for these
        shutil.rmtree("resources/he")

    def test_extract_execute_HE(self):
        # extract HE
        extractor = HumanEvalExtraction()
        data = extractor.extract("resources/humanevaltest/datasets/HumanEval.jsonl.gz", "resources/he")

        # TODO currently under construction 26.04.2024    error:      cat: out: No such file or directory
        executor = HumanEvalExecutor(debug=True)
        for d in data[:3]:
            results = executor.execute("code" , "tests", d)
            print("ID__________________" , d["id"])
            if not results[0]:
               print("ERROR:" , results)
        shutil.rmtree("resources/he")
