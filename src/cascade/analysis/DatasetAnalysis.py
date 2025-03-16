import os
import re
import shutil
import tempfile

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.extraction.JavaExtraction import JavaExtraction

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, save_dicts_list_to_json

from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class DatasetAnalysis(Analysis):
    def __init__(self, generator: Generation, executor: Execution, regenerate=False, reexecute=False, image="maven" , debug=0, step_size=1):
        super().__init__(generator, executor)
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.image = image


    def analyse(self, data: list, input_path, output_path):
        """
        This is the main analysis of the dataset.
        It will run the analysis on single methods as they are provided in the dataset.

        :param data: a list wit hone element. The context dictionary for the method under test.
        :param input_path
        :param output_path:
        """

        output = ""
        ana_path = os.path.join(output_path, "analyzed.json")

        # load data for this specific run.
        data = load_json_from_path(ana_path)

        # take the one element that is targeted here.
        d = data[0]

        test_class_real_name = d["test_file_path"].split("/")[-1].split(".")[0]
        test_class_unique_name = "THIS_IS_A_UNIQUE_NAME_Test"

        if not "test_package" in d:
            print("no original tests were found for this method")
            d["test_package"] = d["package"]


        print(f"  Starting analysis of function: {d['signature']['name']}")
        print("    Step 1 - New Tests")

        if not "new_tests" in d:
            new_tests, chat_history = self.generator.generate_tests(d, input_path, output_path)

            d["new_tests"] = new_tests
            d["new_tests_history"] = chat_history
            save_dicts_list_to_json([d], ana_path)

            if new_tests == "":
                return

        else:
            print("      new tests already generated")

        print("      execute new tests")

        d["results"] = {}
        d["results"]["(code, new_tests)"] = [[],[],[]]

        d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
        d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)
        exec_results = self.executor.execute("code", "new_tests", d, input_path, output_path)

        res1 = list(exec_results[0])
        comp_errors = exec_results[1]

        with open(output_path + "/log.txt", "a") as f:
            f.write("COMP ERRORS:" + str(comp_errors) + "\n-------\n")
        d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
        d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
        if comp_errors:
            comp_errors = comp_errors.replace(test_class_unique_name, test_class_real_name)

        evaluated = self.evaluate(res1)

        # this is the compilation error loop.  so far hard coded number for tries. TODO could be a parameter
        max_repair_tries = 2
        current_repair_tries = 0
        for i in range(max_repair_tries):
            # repair step
            # if there were actually compiler errors with the tests:
            if evaluated == 0 and comp_errors:
                current_repair_tries += 1
                print("      Try to generate repaired tests")
                repaired_tests, _ = self.generator.repair_tests(d, input_path, output_path, comp_errors, 'new_tests')

                old_tests_key = "tests_pre_repairstep_" + str(i + 1)
                d[old_tests_key] = d["new_tests"]
                d["new_tests"] = repaired_tests

                print("      execute repaired tests")

                d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
                d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)

                res1, comp_errors = self.executor.execute("code", "new_tests", d, input_path, output_path)
                res1 = list(res1)

                d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
                d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
                if comp_errors:
                    comp_errors = comp_errors.replace(test_class_unique_name, test_class_real_name)

                evaluated = self.evaluate(res1)
                save_dicts_list_to_json([d], ana_path)


        amount_res = [len(r) for r in res1]
        d["results"]["(code, new_tests)"] = res1

        next_phase = False
        if evaluated == 0:
            # loggin ----------
            with open(output_path + "/errors.txt", "a") as f:
                f.write(f"S1 Error in tests")
                f.write(f"{str(res1)}")
                f.write("------\nTests:\n")
                f.write(f"{d["new_tests"]}\n")
                f.write("------\nCode:\n")
                f.write(d["code"])
                if comp_errors:
                    f.write("\n------\nCompiler errors:\n")
                    f.write(comp_errors)
                else:
                    f.write("\n-------\nNo Compiler errors.  check log\n")
                f.write("-----------------------\n")

            output = f"Negative; error; step 1 (C +T'); {str(amount_res)}; ; "
            print(output)

        elif evaluated == 1:
            output = f"Negative; pass; step 1 (C +T'); {str(amount_res)}; ; "
            print(output)

        else:
            next_phase = True
        save_dicts_list_to_json([d], ana_path)

        if next_phase:
            # generate new code  -----------------------------------------------------------------------------------------------
            print("    Step 2 - New Code")
            d["results"]["(new_code, new_tests)"] = [[], [], []]
            new_code, response = self.generator.generate_code(d, input_path, output_path)
            #TODO overhaul code generation?
            d["new_code"] = new_code
            d["new_code_response"] = response
            print("      execute new code (with new tests)")

            d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
            d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)

            res2, comp_errors = self.executor.execute("new_code", "new_tests", d, input_path, output_path)
            res2 = list(res2)

            d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
            d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
            if comp_errors:
                comp_errors = comp_errors.replace( test_class_unique_name , test_class_real_name )

            evaluated2 = self.evaluate(res2)

            #TODO repair loop for code?
            save_dicts_list_to_json([d], ana_path)

            amount_res2 = [len(r) for r in res2]
            d["results"]["(new_code, new_tests)"] = res2

            next_phase = False
            if evaluated2 == 0:
                # loggin ----------
                with open(output_path + "/errors.txt", "a") as f:
                    f.write(f"S2 Error in code?")
                    f.write(f"{str(res1)}")
                    f.write("------\nTests:\n")
                    f.write(f"{d["new_tests"]}\n")
                    f.write("------\nCode:\n")
                    f.write(d["code"])
                    if comp_errors:
                        f.write("\n------\nCompiler errors:\n")
                        f.write(comp_errors)
                    else:
                        f.write("\n-------\nNo Compiler errors.  check log\n")
                    f.write("-----------------------\n")

                output = f"Negative; error; step 2 (C'+T'); {str(amount_res)}; {str(amount_res2)}"
                print(output)

            elif evaluated2 == 1:
                output = f"Positive; pass; step 2 (C'+T'); {str(amount_res)}; {str(amount_res2)}"
                print(output)

            else:
                output = f"Negative; fail; step 2 (C'+T'); {str(amount_res)}; {str(amount_res2)}"

            # calculate the new improved metrix for checking out if something is a positive or not.
            r1 = [d["results"]["(code, new_tests)"][0], d["results"]["(code, new_tests)"][1] + d["results"]["(code, new_tests)"][2]]
            r2 = [d["results"]["(new_code, new_tests)"][0], d["results"]["(new_code, new_tests)"][1] + d["results"]["(new_code, new_tests)"][2]]

            metric = {"vv": [], "vx": [], "xx": [], "xv": []}

            for i in r1[0]:
                if i in r2[0]:
                    metric["vv"].append(i)
                elif i in r2[1]:
                    metric["vx"].append(i)
            for i in r1[1]:
                if i in r2[0]:
                    metric["xv"].append(i)
                elif i in r2[1]:
                    metric["xx"].append(i)
            d["metric"] = metric

            save_dicts_list_to_json([d], ana_path)
            metric_lengths = ", ".join(f"{k}: {len(v)}" for k, v in metric.items())
            output += f"; {metric_lengths}"

        save_dicts_list_to_json([d], ana_path)
        with open("result.txt", "w") as f:
            output+= f"; {str("og tests exist" if "tests" in d else " no og tests")}; {current_repair_tries}"
            f.write(output)
            print("result:" , output)

        self.executor.tear_down(data)


    def evaluate(self, res):
        if res[0] == [] and res[1] == [] and res[2] == []:
            print("        Error")
            # error
            return 0
        elif res[1] == [] and res[2] == []:
            print("        Passed")
            # if no errors or failures  then passed
            return 1
        else:
            print("        Failed")
            return -1

