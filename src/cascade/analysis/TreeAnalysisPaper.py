import os
import re

from tqdm import tqdm

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.visualizer.Visualization import Visualization

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, log, save_dicts_list_to_json


class TreeAnalysisPaper(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization, regenerate=False, reexecute=False, debug=0, step_size=1, die_if_setup_fails=False):
        super().__init__(generator, executor, visualizer)
        self.die_if_setup_fails = die_if_setup_fails
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.visualizer.logger = "tqdm"


    def analyse(self, data: list, input_path, output_path):
        # allows setting up requirements needed in every step of the execution (i.e. load docker images )
        print("Set up started")
        if not self.executor.set_up(data, input_path, output_path) and self.die_if_setup_fails:
            print("Set up failed")
            return
        print("Set up finished")

        #  loop through data
        for d in tqdm(data[::self.step_size]):
            dirty = False

            if self.debug >= 2:
                self.visualizer.visualize(data, output_path)

            # Level 1  code + test: --------------------------------------

            if "id" in d and d["id"] != "":
                log(d["id"], logger="tqdm")
            else:
                log(d["signature"]["name"], logger="tqdm")
            log("    Level 1", logger="tqdm")

            if "results" not in d:
                d["results"] = {}
            if self.reexecute or "(code, tests)" not in d["results"]:
                if self.debug >= 1:
                    log("        Executing code, tests", logger="tqdm")

                try:
                    res1 = self.executor.execute("code", "tests", d, input_path, output_path)
                except:
                    d["results"]["(code, tests)"] = [[], [], []]
                    continue

                if self.debug >= 1:
                    log("        Finished executing code, tests", logger="tqdm")
                dirty = True

            else:
                res1 = d["results"]["(code, tests)"]


            # check and sort stuff
            d["results"]["(code, tests)"] = list(res1)
            if dirty:
                save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
                dirty = False

            evaluated = self.evaluate(d["results"]["(code, tests)"])

            if evaluated <= 0:
                continue
            del res1

            # Level 2   code + new_test: ---------------------------------
            log("    Level 2", logger="tqdm")

            if "new_tests" not in d or self.regenerate:

                if self.debug >= 1:
                    log("        Generating new tests", logger="tqdm")
                try:
                    new_tests, response = self.generator.generate_tests(d, input_path, output_path)
                    d["new_tests"] = new_tests

                except:
                    d["new_tests"] = []
                    d["new_tests_response"] = []
                    continue

                if self.debug >= 1:
                    log("        Finished generating new tests", logger="tqdm")

                d["new_tests"] = new_tests
                d["new_tests_response"] = response
                dirty = True

            if self.reexecute or "(code, new_tests)" not in d["results"]:
                if self.debug >= 1:
                    log("        Executing code, new_tests", logger="tqdm")

                try:
                    res2 = self.executor.execute("code", "new_tests", d, input_path, output_path)
                    d["results"]["(code, new_tests)"] = list(res2)
                except:
                    d["results"]["(code, new_tests)"] = [[], [], []]
                    continue

                evaluated = self.evaluate(d["results"]["(code, new_tests)"])

                if evaluated == 0:
                    with open(output_path + "/log.txt", "r") as f:
                        exec_output = f.read()
                    # If it errored we want to know the compilation error:

                    matches = re.findall(r'\[ERROR\] COMPILATION ERROR :[\s\S]*?\[INFO\] -*\n(.*?)\[INFO\]',
                                         exec_output,
                                         re.DOTALL)

                    if not matches:
                        # No match (compilation error) found.
                        with open(output_path + "/log.txt", "a") as f:
                            f.write("No compilation error found\n")

                    else:
                        # Get the last occurrence
                        comp_error = matches[-1].strip()

                        new_tests, response = self.generator.repair_tests(d, input_path, output_path, comp_error,
                                                                          'new_tests')

                        d["new_tests"] = new_tests

                        print("execute repaired tests")
                        res2 = list(self.executor.execute("code", "new_tests", d, input_path, output_path))

                        d["results"]["(code, new_tests)"] = list(res2)
                        evaluated = self.evaluate(d["results"]["(code, new_tests)"])

                if self.debug >= 1:
                    log("        Finished executing code, new_tests", logger="tqdm")

                dirty = True
            else:
                res2 = d["results"]["(code, new_tests)"]

            d["results"]["(code, new_tests)"] = list(res2)

            if dirty:
                save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
                dirty = False

            test_safety_copy_path = os.path.join(output_path, "test_generator_current.json")
            if os.path.exists(test_safety_copy_path):
                os.remove(test_safety_copy_path)

            if evaluated >= 0 :
                continue
            del res2

            log("    Level 3", logger="tqdm")

            # Level 3   new_code + new_test: ---------------------------------
            if "new_code" not in d or self.regenerate:
                if self.debug >= 1:
                    log("        Generating new code", logger="tqdm")

                try:
                    new_code, response = self.generator.generate_code(d, input_path, output_path)
                except:
                    d["new_code"] = []
                    d["new_code_response"] = []
                    continue

                if self.debug >= 1:
                    log("        Finished generating new code", logger="tqdm")

                d["new_code"] = new_code
                if self.debug >= 3:
                    d["new_code_response"] = response
                dirty = True

            if self.reexecute or "(new_code, new_tests)" not in d["results"]:
                if self.debug >= 1:
                    log("        Executing new_code, new_tests", logger="tqdm")

                try:
                    res3 = self.executor.execute("new_code", "new_tests", d, input_path, output_path)
                except:
                    d["results"]["(new_code, new_tests)"] = [[], [], []]
                    continue

                if self.debug >= 1:
                    log("        Finished executing new_code, new_tests", logger="tqdm")

                dirty = True
            else:
                res3 = d["results"]["(new_code, new_tests)"]

            d["results"]["(new_code, new_tests)"] = list(res3)

            if dirty:
                save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
                dirty = False

            code_safety_copy_path = os.path.join(output_path, "code_generator_current.json")
            if os.path.exists(code_safety_copy_path):
                os.remove(code_safety_copy_path)

            evaluated = self.evaluate(d["results"]["(new_code, new_tests)"])

            if evaluated == 0:
                with open(output_path + "/log.txt", "r") as f:
                    exec_output = f.read()
                # If it errored we want to know the compilation error:

                matches = re.findall(r'\[ERROR\] COMPILATION ERROR :[\s\S]*?\[INFO\] -*\n(.*?)\[INFO\]',
                                     exec_output, re.DOTALL)

                if not matches:
                    # No match (compilation error) found.
                    with open(output_path + "/log.txt", "a") as f:
                        f.write("No compilation error found\n")

                else:
                    # Get the last occurrence
                    comp_error = matches[-1].strip()

                    new_code, response = self.generator.repair_code(d, input_path, output_path, comp_error,
                                                                    'new_code')

                    d["new_code"] = new_code
                    d["new_code_repair_response"] = response

                    print("execute repaired code")
                    res3 = list(self.executor.execute("new_code", "new_tests", d, input_path, output_path))

                    d["results"]["(new_code, new_tests)"] = list(res3)

                    evaluated = self.evaluate(d["results"]["(new_code, new_tests)"])


            if evaluated <= 0:
                continue
            del res3

            log("    Level 4", logger="tqdm")

            if self.reexecute or "(new_code, tests)" not in d["results"]:
                if self.debug >= 1:
                    log("        Executing new_code, tests", logger="tqdm")

                try:
                    res4 = self.executor.execute("new_code", "tests", d, input_path, output_path)
                except:
                    d["results"]["(new_code, tests)"] = [[], [], []]
                    continue

                if self.debug >= 1:
                    log("        Finished executing new_code, tests", logger="tqdm")

                dirty = True
            else:
                res4 = d["results"]["(new_code, tests)"]

            d["results"]["(new_code, tests)"] = list(res4)

            if dirty:
                save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

            evaluated = self.evaluate(d["results"]["(new_code, tests)"])
            if evaluated == 0:
                continue
            del res4

        self.executor.tear_down(data)

        self.visualizer.visualize(data, output_path, full=True)

    def evaluate(self, res):
        if res[0] == [] and res[1] == []:
            if self.debug >= 1:
                print("        Error")
            # error
            return 0
        elif res[1] == [] and res[2] == []:
            if self.debug >= 1:
                print("        Passed")
            # if no errors or failures  then passed
            return 1
        else:
            if self.debug >= 1:
                print("        Failed")
            # failed
            return -1
