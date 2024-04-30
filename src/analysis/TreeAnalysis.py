import os

from src.analysis.Analysis import Analysis

from src.generation.Generation import Generation
from src.analysis.executor.AnalysisExecutor import AnalysisExecutor
from src.analysis.visualizer.AnalysisVisualizer import AnalysisVisualizer

from src.utils.Utils import save_dicts_list_to_json, load_json_from_path


class TreeAnalysis(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: AnalysisExecutor, visualizer: AnalysisVisualizer, regenerate=False):
        super().__init__(generator, executor, visualizer)
        self.regenerate = regenerate

    def analyse(self, data: list, output_path):
        """
        TODO
        :param output_path:
        :param data:
        :return:
        """

        if not self.regenerate:
            temp_data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
            if temp_data:
                data = temp_data

        #  loop through data
        for d in data:
            self.visualizer.visualize(data)
            print("--------------")

            # Phase 1  code + test: --------------------------------------
            print(d["id"])
            #print("    Level 1")
            res1 = self.executor.execute("code", "tests", d)
            # check and sort stuff
            d["results"] = {"(code, tests)": list(res1)}

            if res1[0] == [] and res1[1] == []:
                # error
                continue
            elif res1[1] == [] and res1[2] == []:
                # if no errors or failures  then passed
                pass
            else:
                # failed
                continue

            # Level 2   code + new_test: ---------------------------------
            #print("    Level 2")
            if "new_tests" not in d:
                new_tests, _ = self.generator.generate_tests(d, output_path)
                #test #new_tests = "import unittest\nfrom func import *\n\nclass test_func(unittest.TestCase):\n" +"    def test_specialFilter(self):\n        self.assertEqual(specialFilter([15, -73, 14, -15]), 1)\n        self.assertEqual(specialFilter([33, -2, -3, 45, 21, 109]), 2)\n        self.assertEqual(specialFilter([1, 3, 5, 7, 9, 11, 13, 15, 17, 19]), 10)\n        self.assertEqual(specialFilter([2, 4, 6, 8, 10, 12, 14, 16, 18, 20]), 0)\n        self.assertEqual(specialFilter([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), 0)\n\nif __name__ == '__main__':\n    unittest.main()"

                d["new_tests"] = new_tests

            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

            res2 = self.executor.execute("code","new_tests", d)
            d["results"]["(code, new_tests)"] = list(res2)

            if res2[0] == [] and res2[1] == []:
                # error
                continue
            elif res2[1] == [] and res2[2] == []:
                # if no errors or failures  then passed
                continue
            else:
                # failed
                pass

            #print("    Level 3")

            # Level 3   new_code + new_test: ---------------------------------
            if "new_code" not in d:
                new_code, response = self.generator.generate_code(d, output_path)
                d["new_code"] = new_code


            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

            res3 = self.executor.execute("new_code", "new_tests", d)
            d["results"]["(new_code, new_tests)"] = list(res3)

            if res3[0] == [] and res3[1] == []:
                # error
                continue
            elif res3[1] == [] and res3[2] == []:
                # if no errors or failures  then passed
                pass
            else:
                # failed
                continue
            print(res3)


            #print("    Level 4")
            res4 = self.executor.execute("new_code", "tests", d)
            d["results"]["(new_code, tests)"] = list(res4)

            if res4[0] == [] and res4[1] == []:
                # error
                continue
            elif res4[1] == [] and res4[2] == []:
                # if no errors or failures  then passed
                pass
            else:
                # failed
                pass

        self.visualizer.visualize(data)
        print("--------------")







        # for each thing in data DO:
        #

        #       phase 1 code + test
        #
        #
        #

