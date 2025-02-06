import os
import re
import shutil
import tempfile

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.visualizer.Visualization import Visualization
from cascade.extraction.JavaExtraction import JavaExtraction

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, log, save_dicts_list_to_json

from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class DatasetAnalysis(Analysis):
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization, regenerate=False, reexecute=False, image="maven" , debug=0, step_size=1):
        super().__init__(generator, executor, visualizer)
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.visualizer.logger = "tqdm"
        self.image = image

    def extract_junit_version(self, input_path, output_path):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.copytree(input_path, temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            dock_ex = DockerizedWrapper(debug=0)

            # get the effective pom file, which usually contains the used junit version
            dock_context = {
                "image" : self.image,
                "directory" : temp_dir,
                "command" : "mvn help:effective-pom -Doutput=effective-pom.xml",
                "path" : "/root/effective-pom.xml"
            }

            dock_ex.execute(dock_context, output_path, copy=True)

        try:
            tree = ET.parse(os.path.join(output_path, "effective-pom.xml"))
            root = tree.getroot()

            # Define namespaces, if they exist in your pom.xml
            namespaces = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Default Maven namespace

            # Initialize variables for return values
            junit_version = "JUnit dependency not found"
            source_dir = "Source directory not specified"
            test_source_dir = "Test source directory not specified"

            # Search for JUnit dependency
            for dependency in root.findall(".//m:dependency", namespaces):
                group_id = dependency.find("m:groupId", namespaces)
                artifact_id = dependency.find("m:artifactId", namespaces)
                if group_id is not None and artifact_id is not None:
                    if group_id.text == "junit" and artifact_id.text == "junit":
                        version = dependency.find("m:version", namespaces)
                        if version is not None:
                            junit_version = version.text
                        else:
                            junit_version = "Version not specified"

            # Extract source and test source directories
            build = root.find(".//m:build", namespaces)
            if build is not None:
                source_directory = build.find("m:sourceDirectory", namespaces)
                test_source_directory = build.find("m:testSourceDirectory", namespaces)

                if source_directory is not None:
                    source_dir = source_directory.text
                if test_source_directory is not None:
                    test_source_dir = test_source_directory.text

            # Return a 3-tuple with JUnit version, source directory, and test source directory
            return junit_version, source_dir, test_source_dir

        except ET.ParseError as e:
            return f"Error parsing pom.xml: {e}", None, None

    def analyse(self, data: list, input_path, output_path):
        """
        This is the new and improved analysis.  it does not use or require the original tests.

        :param data:
        :param input_path:
        :param output_path:
        """

        output = ""

        ana_path = os.path.join(output_path, "analyzed.json")

        # load data for this specific run.
        data = load_json_from_path(ana_path)

        d = data[0]

        # extract functions   I DONT KNOW WHY THIS WAS HERE?
        #extractor = JavaExtraction()
        #extractor.extract(input_path, output_path)

        if "junit_version" not in d or "test_file_path" not in d:
            print(output_path)
            print("extracting Junit version")
            junit_version, source_dir, test_source_dir = self.extract_junit_version(input_path, output_path )
            print("Junit version: ", junit_version)

            if test_source_dir is not None and source_dir is not None:
                d["test_file_path"] = d["code_file_path"].replace(source_dir.replace("/root/" , ""), test_source_dir.replace("/root/" , ""))
                d["test_file_path"] = d["test_file_path"].replace(".java", "Test.java")
            else:
                d["test_file_path"] = d["code_file_path"].replace(".java", "Test.java")

            d["junit_version"] = junit_version
            save_dicts_list_to_json([d], ana_path)

            # basically a one step thing to run once over the dataset to provide all nesscary information. thats why we return here.
            return

        else:
            junit_version = d["junit_version"]

        test_class_real_name = d["test_file_path"].split("/")[-1].split(".")[0]
        test_class_unique_name = "THIS_IS_A_UNIQUE_NAME_Test"

        # found in imports ?
        junit_found = False

        if not "test_package" in d:
            print("no original tests were found for this method")
            d["test_package"] = d["package"]

        else:
            for imp in d["test_imports"]:
                if "junit" in imp:
                    junit_found = True
                    break

        if not junit_found:
            if junit_version.startswith("3"):
                d["test_imports"] = ["import junit.framework.*;\n"]
            elif junit_version.startswith("4."):
                d["test_imports"] = ["import org.junit.*;\n" , "import static org.junit.Assert.*;\n"]
            else:
                d["test_imports"] = ["import org.junit.jupiter.api.*;\n"]


        print(f"Starting analysis of function: {d['signature']['name']}")
        print("  Step 1 - New Tests")

        if not "new_tests" in d:
            new_tests, chat_history = self.generator.generate_tests(d, input_path, output_path)

            d["new_tests"] = new_tests
            d["new_tests_history"] = chat_history   #for debugging only

        else:
            print("    new tests already generated")

        print("    execute new tests")

        d["results"] = {}
        d["results"]["(code, new_tests)"] = [[],[],[]]


        d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
        d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)
        exec_results = self.executor.execute("code", "new_tests", d, input_path, output_path)
        res1 = list(exec_results [0])
        comp_errors = exec_results[1]
        with open(output_path + "/log.txt", "a") as f:
            f.write("COMP ERRORS:" + str(comp_errors) + "\n-------\n")
        d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
        d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
        if comp_errors:
            comp_errors = comp_errors.replace(test_class_unique_name, test_class_real_name)


        evaluated = self.evaluate(res1)

        # this is the compilation error loop.  turn back on if needed by either making this a true or removing the check.
        repairloop_tests = True
        repair_tries = 0
        if repairloop_tests:
            for i in range(2):
                # repair step
                if evaluated == 0 and comp_errors:
                    repair_tries += 1
                    print("        Try to generate repaired tests")
                    repaired_tests , _ = self.generator.repair_tests(d, input_path, output_path, comp_errors, 'intermediate_test')

                    d["new_tests"] = repaired_tests

                    print("        execute repaired tests")

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
        d["results"]["(code, new_tests)"] = amount_res

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

            output = f"Negative, error, step 1 (C +T'), {str(amount_res)}, "
            print(output)

        elif evaluated == 1:
            output = f"Negative, pass, step 1 (C +T'), {str(amount_res)}, "
            print(output)

        else:
            next_phase = True

        if next_phase:
            # generate new code  -----------------------------------------------------------------------------------------------
            print("  Step 2 - New Code")
            d["results"]["(new_code, new_tests)"] = [[], [], []]
            new_code, response = self.generator.generate_code(d, input_path, output_path)
            #TODO overhaul code generation?
            d["new_code"] = new_code
            d["new_code_response"] = response
            print("    execute new code (with new tests)")

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
            d["results"]["(code, new_tests)"] = amount_res2

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

                output = f"Negative, error, step 2 (C'+T'), {str(amount_res)}, {str(amount_res2)}]"
                print(output)

            elif evaluated2 == 1:
                output = f"Positive, pass, step 2 (C'+T'), {str(amount_res)}, {str(amount_res2)}"
                print(output)

            else:
                output = f"Negative, fail, step 2 (C'+T'), {str(amount_res)}, {str(amount_res2)}"

        with open("result.txt", "w") as f:
            output+= f", {str(True if "tests" in d else False)}, {repair_tries}"
            f.write(output)
            print("result:" , output)

        self.executor.tear_down(data)


#             for test in d["new_tests"]:
#                 if test["phase1"] == "fail" or test["phase1"] == "pass":  # errors ignroed.  passes should still pass
#                     print("        testing property:", test["property"])
#
#                     test["test_class"] = test["test_class"].replace(test_class_real_name, test_class_unique_name)
#                     d["intermediate_test"] = test["test_class"]
#                     d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)
#
#                     res2, comp_errors = self.executor.execute("new_code", "intermediate_test", d, input_path, output_path)
#                     res2 = list(res2)
#
#                     print("RES:" + str(res2))
#                     print("COMP ERRORS:" + str(comp_errors))
#
#                     test["test_class"] = test["test_class"].replace(test_class_unique_name, test_class_real_name)
#                     d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
#                     if comp_errors:
#                         comp_errors = comp_errors.replace( test_class_unique_name , test_class_real_name )
#
#                     evaluated = self.evaluate(res2)
#
#
#                     if evaluated == 0:
#                         # loggin ----------
#                         with open(output_path + "/errors.txt", "a") as f:
#                             f.write(f"S2 Error in test: {test["property"]}\n")
#                             f.write(f"{str(res2)}")
#                             f.write(f"{test["test_class"]}\n")
#                             f.write("------\nCode:\n")
#                             f.write(d["new_code"])
#                             if comp_errors:
#                                 f.write("\n------\nCompiler errors:\n")
#                                 f.write(comp_errors)
#                             else:
#                                 f.write("\n-------\nNo Compiler errors.  check log\n")
#                             f.write("-----------------------\n")
#
#                         d["results"]["(new_code, new_tests)"][2].append({"property" : test["property"] , "results": res2})
#                         test["phase2"] = "error"
#
#                     elif evaluated == 1:
#                         d["results"]["(new_code, new_tests)"][0].append({"property" : test["property"] , "results": res2})
#                         test["phase2"] = "pass"
#
#                     else:
#                         d["results"]["(new_code, new_tests)"][1].append({"property" : test["property"] , "results": res2})
#                         test["phase2"] = "fail"
#
#                     save_dicts_list_to_json([d], ana_path)
#
#
#             # check if it errored
#             print("    evaluate overall results for function (s2):", end="")
#             evaluated_full = self.evaluate(d["results"]["(new_code, new_tests)"])
#
#             # TODO still needs to be adjusted for new format
#             # repairloop_code = False
#             # if repairloop_code:
#             #     for i in range(1):
#             #         if evaluated == 0 and comp_errors:
#             #
#             #             new_code, response = self.generator.repair_code(d, input_path, output_path, comp_errors, 'new_code')
#             #             d["new_code"] = new_code
#             #             print("        execute repaired code")
#             #
#             #             # TODO is the intermediate test realy the best option here? shoudl we change the acutall code or just the instance that is for this specific test???
#             #             d["intermediate_test"] = d["intermediate_test"].replace(test_class_real_name, test_class_unique_name)
#             #             d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)
#             #
#             #             res2, comp_errors = self.executor.execute("new_code", "intermediate_test", d, input_path, output_path)
#             #             res2 = list(res2)
#             #
#             #             d["intermediate_test"] = d["intermediate_test"].replace(test_class_unique_name, test_class_real_name)
#             #             d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
#             #             if comp_errors:
#             #                 comp_errors = comp_errors.replace(test_class_unique_name, test_class_real_name)
#             #
#             #             evaluated = self.evaluate(res2)
#             #
#             #             save_dicts_list_to_json([d], ana_path)
#
#             lengths2 = [len(d["results"]["(new_code, new_tests)"][i]) for i in range(3)]
#             if lengths2[0] > 0 and lengths2[1] == 0:
#                 # ALL passed (or errored)
#                 output = f"Positive, pass  in step 2 (C'+T') [{lengths[0]},{lengths[1]},{lengths2[2]}][{lengths2[0]},{lengths2[1]},{lengths2[2]}]"
#                 output += f"  junit: {junit_version}"
#
#             elif lengths2[1] > 0:
#                 # some failed
#                 output = f"Negative, fail in step 2 (C'+T') [{lengths[0]},{lengths[1]},{lengths2[2]}][{lengths2[0]},{lengths2[1]},{lengths2[2]}]"
#                 output += f"  junit: {junit_version}"
#
#             else:
#                 output = f"Negative, error in step 2 (C'+T') [{lengths[0]},{lengths[1]},{lengths2[2]}][{lengths2[0]},{lengths2[1]},{lengths2[2]}]"
#                 output += f"  junit: {junit_version}"




    def evaluate(self, res):
        if res[0] == [] and res[1] == [] and res[2] == []:
            print("            Error")
            # error
            return 0
        elif res[1] == [] and res[2] == []:
            print("            Passed")
            # if no errors or failures  then passed
            return 1
        else:
            print("            Failed")
            return -1
