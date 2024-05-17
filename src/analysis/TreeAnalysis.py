import os

from tqdm import tqdm

from src.analysis.Analysis import Analysis
from src.analysis.executor.Execution import Execution
from src.analysis.visualizer.Visualization import Visualization

from src.generation.Generation import Generation

from src.utils.Utils import *


class TreeAnalysis(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization, regenerate=False, reexecute=False, debug=False, step_size=1):
        super().__init__(generator, executor, visualizer)
        self.reexecute = reexecute
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.visualizer.logger = "tqdm"




    def analyse(self, data: list, output_path):
        """
        TODO
        :param output_path:
        :param data:
        :return:
        """

        # generated artifacts for the same dataset can be saved to avoid repeated generation of code and tests.
        if not self.regenerate:
            temp_data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
            if temp_data:
                data = temp_data

        # allows seting up requieremnts needed in every step of the execution (i.e. load docker images )
        self.executor.set_up(data)

        #  loop through data
        for d in tqdm(data[::self.step_size]):


            if self.debug:
                self.visualizer.visualize(data)

            # Phase 1  code + test: --------------------------------------



            if "id" in d and d["id"] != "":
                log(d["id"], logger="tqdm")
            else:
                log(d["signature"]["name"], logger="tqdm")
            log("    Level 1", logger="tqdm")


            if "results" not in d:
                d["results"] = {}
            if self.reexecute or "(code, tests)" not in d["results"]:
                res1 = self.executor.execute("code", "tests", d)
            else:
                res1 = d["results"]["(code, tests)"]

            # check and sort stuff
            d["results"]["(code, tests)"] = list(res1)

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
            log("    Level 2", logger="tqdm")

            if "new_tests" not in d:
                new_tests, response = self.generator.generate_tests(d, output_path)
                #test #new_tests = "import unittest\nfrom func import *\n\nclass test_func(unittest.TestCase):\n" +"    def test_specialFilter(self):\n        self.assertEqual(specialFilter([15, -73, 14, -15]), 1)\n        self.assertEqual(specialFilter([33, -2, -3, 45, 21, 109]), 2)\n        self.assertEqual(specialFilter([1, 3, 5, 7, 9, 11, 13, 15, 17, 19]), 10)\n        self.assertEqual(specialFilter([2, 4, 6, 8, 10, 12, 14, 16, 18, 20]), 0)\n        self.assertEqual(specialFilter([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), 0)\n\nif __name__ == '__main__':\n    unittest.main()"

                d["new_tests"] = new_tests
                d["new_tests_response"] = response

            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

            #
            test_safety_copy_path = os.path.join(output_path, "test_generator_current.json")
            if os.path.exists(test_safety_copy_path):
                os.remove(test_safety_copy_path)

            if self.reexecute or "(code, new_tests)" not in d["results"]:
                res2 = self.executor.execute("code", "new_tests", d)
            else:
                res2 = d["results"]["(code, new_tests)"]

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


            log("    Level 3", logger="tqdm")

            # Level 3   new_code + new_test: ---------------------------------
            if "new_code" not in d:
                new_code, response = self.generator.generate_code(d, output_path)
                d["new_code"] = new_code
                d["new_code_response"] = response


            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

            if self.reexecute or "(new_code, new_tests)" not in d["results"]:
                res3 = self.executor.execute("new_code", "new_tests", d)
            else:
                res3 = d["results"]["(new_code, new_tests)"]

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

            log("    Level 4", logger="tqdm")

            if self.reexecute or "(new_code, tests)" not in d["results"]:
                res4 = self.executor.execute("new_code", "tests", d)
            else:
                res4 = d["results"]["(new_code, tests)"]

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


        save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))


        self.executor.tear_down(data)


        self.visualizer.visualize(data, full=True)
