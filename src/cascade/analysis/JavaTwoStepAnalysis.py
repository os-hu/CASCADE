import json
import os
import shutil
import tempfile
from datetime import datetime
from tqdm import tqdm

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.executor.ExecutionResults import ExecutionResults

from cascade.generation.Generation import Generation
from cascade.utils.Utils import save_dicts_list_to_json, load_json_from_path

from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class JavaTwoStepAnalysis(Analysis):
    def __init__(self,
                 generator: Generation,
                 executor: Execution,
                 regenerate=False,
                 reexecute=False,
                 image="maven" ,
                 debug=0,
                 step_size=1,
                 max_repair_tries=3
                 ):
        super().__init__(generator, executor)
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.image = image
        self.output_path = ""
        self.max_repair_tries = max_repair_tries


    def analyze(self, data: list, input_path, output_path):
        """
        This is the main analysis tool

        :param data: a list with the methods from the program under test. Contains a context dictionary for each method under test.
        :param input_path:
        :param output_path:
        """
        def log(header, message):
            with open(os.path.join(output_path, "log.txt"), "a") as f:
                f.write(header + "\n")
                f.write(message+ "\n")

        # TODO refactor and actually use these...
        def has_nonempty(dct, key: str) -> bool:
            return key in dct and isinstance(dct[key], str) and dct[key].strip() != ""

        def has_results(dct, results_key: str) -> bool:
            return "results" in dct and results_key in dct["results"] and dct["results"][results_key] not in (None, [], [[], [], []])

        def should_generate(dct, key: str) -> bool:
            # regenerate forces regeneration
            return self.regenerate or (key not in dct)

        def should_execute(dct, results_key: str) -> bool:
            # reexecute forces execution
            return self.reexecute or (not has_results(dct, results_key))




        print(f"analyzing {len(data)} elements")

        #TODO check if the intermedatie reustls can / shoudl be used somewehre
        if os.path.exists(os.path.join(output_path, "analyzed.json")):
            data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
            print(f"loaded existing analyzed data with {len(data)} elements")
        else:
            # preparing/ finding out junit version etc.
            data = self.prepare_data(data, input_path, output_path)
            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

        print("setup executor mvn image")
        self.executor.set_up(data, input_path, output_path)

        time_start = datetime.now()
        for idx, d in enumerate(data):
            try:
                # to avoid name clashes with existing tests we define a unique name for the test class
                test_class_real_name = d["test_file_path"].split("/")[-1].split(".")[0]
                test_class_unique_name = "THIS_IS_A_UNIQUE_NAME_Test"

                time_now = datetime.now()
                time_elapsed = time_now - time_start
                time_avg = time_elapsed / (idx + 1)
                time_remaining = time_avg * (len(data) - (idx + 1))

                print(
                    f"{time_now.strftime('%H:%M:%S')}  "
                    f"Analyzing: {d['signature']['name']}. "
                    f"{idx}/{len(data)} "
                    f"time so far: {str(time_elapsed).split('.')[0]} "
                    f"Estimated remaining: {str(time_remaining).split('.')[0]}"
                )


                print("    Step 1 - New Tests")

                if not "new_tests" in d or self.regenerate:
                    print("      generate new tests")
                    new_tests, chat_history = self.generator.generate_tests(d, input_path, output_path)

                    d["new_tests"] = new_tests
                    d["new_tests_history"] = chat_history

                    if new_tests == "":
                        log("GENERATION: no test could be generated.\n ChatHistory:\n", str(chat_history))
                        d["verdict"] = f"NoInco; error; step 1 (C +T'); ; ; "
                        continue

                else:
                    print("      new tests already generated")

                print("      execute new tests")
                d["results"] = {}
                d["results"]["(code, new_tests)"] = [[],[],[]]

                d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
                d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)
                exec_results: ExecutionResults = self.executor.execute("code", "new_tests", d, input_path, output_path)

                res1 = exec_results.results
                comp_errors = exec_results.comp_errors

                log("Results after step 1", str(exec_results))

                d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
                d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
                if comp_errors:
                    comp_errors = comp_errors.replace(test_class_unique_name, test_class_real_name)

                evaluated = self.evaluate(res1)

                # this is the compilation error loop.  so far hard coded number for tries.
                # TODO  currently it is allways regenerating tests if they have compiler errors even if regenerate == False
                d["repair_history"] = []
                for i in range(self.max_repair_tries):
                    # repair step
                    # if there were actually compiler errors with the tests:
                    if evaluated == 0 and comp_errors:
                        print("      Try to generate repaired tests")
                        repaired_tests, response_history = self.generator.repair_tests(d, input_path, output_path, comp_errors, 'new_tests')
                        d["repair_history"].append(response_history)

                        old_tests_key = "tests_pre_repairstep_" + str(i + 1)
                        d[old_tests_key] = d["new_tests"]
                        d["new_tests"] = repaired_tests


                        print("      execute repaired tests")

                        d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
                        d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)

                        exec_results: ExecutionResults = self.executor.execute("code", "new_tests", d, input_path, output_path)
                        res1 = exec_results.results
                        comp_errors = exec_results.comp_errors

                        d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
                        d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)
                        if comp_errors:
                            comp_errors = comp_errors.replace(test_class_unique_name, test_class_real_name)

                        log(f"Results after step 1-Repairstep Nr. {i+1}:" , str(exec_results))

                        evaluated = self.evaluate(res1)

                amount_res = exec_results.results_numbers
                d["results"]["(code, new_tests)"] = res1

                next_phase = False
                if evaluated == 0:
                    # loggin ----------
                    with open(os.path.join(output_path, "errors.txt"), "a") as f:
                        f.write(f"S1 Error in tests")
                        f.write(f"{str(res1)}")
                        f.write("------\nTests:\n")
                        f.write(f"{d['new_tests']}\n")
                        f.write("------\nCode:\n")
                        f.write(d["code"])
                        if comp_errors:
                            f.write("\n------\nCompiler errors:\n")
                            f.write(comp_errors)
                        else:
                            f.write("\n-------\nNo Compiler errors.  check log\n")
                        f.write("-----------------------\n")

                    d["verdict"] = f"NoInco; error; step 1 (C +T'); {str(amount_res)}; ; "

                elif evaluated == 1:
                    d["verdict"] = f"NoInco; pass; step 1 (C +T'); {str(amount_res)}; ; "

                else:
                    #start next phase
                    # generate new code  -----------------------------------------------------------------------------------------------
                    print("    Step 2 - New Code")
                    if not "new_code" in d or self.regenerate:
                        d["results"]["(new_code, new_tests)"] = [[], [], []]
                        print("      generate new code")
                        new_code, response = self.generator.generate_code(d, input_path, output_path)
                        #TODO overhaul code generation?
                        d["new_code"] = new_code
                        d["new_code_response"] = response


                    print("      execute new code (with new tests)")
                    d["new_tests"] = d["new_tests"].replace(test_class_real_name, test_class_unique_name)
                    d["test_file_path"] = d["test_file_path"].replace(test_class_real_name, test_class_unique_name)
                    exec_results: ExecutionResults = self.executor.execute("new_code", "new_tests", d, input_path, output_path)

                    res2 = exec_results.results
                    comp_errors = exec_results.comp_errors

                    log("Results after step 2\n", str(exec_results))

                    d["new_tests"] = d["new_tests"].replace(test_class_unique_name, test_class_real_name)
                    d["test_file_path"] = d["test_file_path"].replace(test_class_unique_name, test_class_real_name)

                    if comp_errors:
                        comp_errors = comp_errors.replace( test_class_unique_name , test_class_real_name )

                    evaluated2 = self.evaluate(res2)

                    amount_res2 = exec_results.results_numbers
                    d["results"]["(new_code, new_tests)"] = res2


                    if evaluated2 == 0:
                        # loggin ----------
                        with open(os.path.join(output_path, "errors.txt"), "a") as f:
                            f.write(f"S2 Error in code?")
                            f.write(f"{str(res1)}")
                            f.write("------\nTests:\n")
                            f.write(f"{d['new_tests']}\n")
                            f.write("------\nCode:\n")
                            f.write(d["code"])
                            if comp_errors:
                                f.write("\n------\nCompiler errors:\n")
                                f.write(comp_errors)
                            else:
                                f.write("\n-------\nNo Compiler errors.  check log\n")
                            f.write("-----------------------\n")

                        d["verdict"] = f"NoInco; error; step 2 (C'+T'); {str(amount_res)}; {str(amount_res2)}"

                    else:
                        # calculate the new improved metrix for checking out if something is a positive or not.
                        r1 = [d["results"]["(code, new_tests)"][0],
                              d["results"]["(code, new_tests)"][1] + d["results"]["(code, new_tests)"][2]]
                        r2 = [d["results"]["(new_code, new_tests)"][0],
                              d["results"]["(new_code, new_tests)"][1] + d["results"]["(new_code, new_tests)"][2]]

                        metric = {"p2p": [], "f2f": [], "p2f": [], "f2p": []}

                        for i in r1[0]:
                            if i in r2[0]:
                                metric["p2p"].append(i)
                            elif i in r2[1]:
                                metric["p2f"].append(i)
                        for i in r1[1]:
                            if i in r2[0]:
                                metric["f2p"].append(i)
                            elif i in r2[1]:
                                metric["f2f"].append(i)

                        d["metric"] = metric
                        metric_lengths = ", ".join(f"{k}: {len(v)}" for k, v in metric.items())

                        if evaluated2 == 1:
                            d["verdict"] = f"INCO; pass; step 2 (C'+T');"

                        else:
                            if len(metric["f2p"]) > 0:
                                d["verdict"] = f"INCO; fail; step 2 (C'+T');"
                            else:
                                d["verdict"] = f"NoInco; fail; step 2 (C'+T');"

                        d["verdict"] += f" {str(amount_res)}; {str(amount_res2)}; {metric_lengths}"

                # end:  if next phase --------------------------------------

                print(d["verdict"])
            except Exception as e:
                d["verdict"] = f"Error during analysis: {e}"

            # quicksave last step.
            with open(os.path.join(output_path, "intermediateResults.jsonl"), "a") as f:
                f.write(json.dumps(d) + "\n")

        # end:  for d in data

        time_end = datetime.now()
        time_total = str(datetime.now() - time_start).split('.')[0],
        print(f"finished analysis ({time_total})")

        self.executor.tear_down(data)
        #save final results
        save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

        stats = {
            "Step1_passed": 0,
            "Step1_failed": 0,
            "Step1_error": 0,
            "Step2_passed": 0,
            "Step2_error": 0,
            "step2_failed": 0,
            "step2_f2p>0": 0,
            "incos" : 0,
            "likely_incos": 0,
        }
        incos = []
        likely_incos = []




        # for d in data:
        #     # TODO check if this is right???
        #     if d["verdict"].startswith("INCO"):
        #         stats["incos"] += 1
        #         incos.append(d)
        #     elif "f2p: 0" not in d["verdict"]:
        #         stats["likely_incos"] += 1
        #         likely_incos.append(d)
        #
        #     if "step 1" in d["verdict"]:
        #         if "pass" in d["verdict"]:
        #             stats["Step1_passed"] += 1
        #         elif "fail" in d["verdict"]:
        #             stats["Step1_failed"] += 1
        #         else:
        #             stats["Step1_error"] += 1
        #     elif "step 2" in d["verdict"]:
        #         if "pass" in d["verdict"]:
        #             stats["Step2_passed"] += 1
        #         elif "fail" in d["verdict"]:
        #             stats["step2_failed"] += 1
        #             if "f2p: 0" not in d["verdict"]:
        #                 stats["step2_f2p>0"] += 1
        #         else:
        #             stats["Step2_error"] += 1


        full_Statistics = {
            "start_time": time_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": time_end.strftime("%Y-%m-%d %H:%M:%S"),
            "total_time": time_total,
            "average_time_per_element": str((datetime.now() - time_start) / len(data)).split('.')[0],
            "analyzed_elements": 0,
        }


        log()





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



    def prepare_data(self, data, input_path, output_path):
        """
        This function prepares the data for the analysis.
        It will check if the data is complete based on the first element and if not it will try to extract the missing information,
        like the junit version and the test file path.
        TODO should be improved to better find different version. Defaulting to Junit5 instead of finding it directly might lead to wrong cases.
        """
        # Helper function ----------------------------------------
        def extract_maven_information():
            junit_version, source_dir, test_source_dir = None, None, None
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    shutil.copytree(input_path, temp_dir, dirs_exist_ok=True)
                except Exception as e:
                    print("could not copy root path")
                    print(e)
                    return None
                dock_ex = DockerizedWrapper()

                # get the effective pom file, which usually contains the used junit version
                dock_context = {
                    "image": self.image,
                    "directory": temp_dir,
                    "command": "mvn help:effective-pom -Doutput=effective-pom.xml",
                    "path": "/root/effective-pom.xml"
                }
                dock_ex.execute(dock_context, output_path, copy=True)

            try:
                tree = ET.parse(os.path.join(output_path, "effective-pom.xml"))
                root = tree.getroot()

                # Search for JUnit dependency
                # Define namespaces, if they exist in the pom.xml
                namespaces = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Default Maven namespace
                for dependency in root.findall(".//m:dependency", namespaces):
                    group_id = dependency.find("m:groupId", namespaces)
                    artifact_id = dependency.find("m:artifactId", namespaces)
                    if group_id is not None and artifact_id is not None:
                        if group_id.text == "junit" and artifact_id.text == "junit":
                            version = dependency.find("m:version", namespaces)
                            if version is not None:
                                junit_version = version.text
                            else:
                                junit_version = "JUnit Version not specified"

                # Extract source and test source directories
                build = root.find(".//m:build", namespaces)
                if build is not None:
                    source_directory = build.find("m:sourceDirectory", namespaces)
                    test_source_directory = build.find("m:testSourceDirectory", namespaces)

                    source_dir = source_directory.text if source_directory is not None else None
                    test_source_dir = test_source_directory.text if test_source_directory is not None else None

                # Return a 3-tuple with JUnit version, source directory, and test source directory
                return junit_version, source_dir, test_source_dir

            except Exception as e:
                return f"Error parsing pom.xml: {e}", None, None
        # Start of the actual function -----------------------------------

        # check junit version once:

        junit_version, source_dir, test_source_dir = None, None, None
        if  "junit_version" not in data[0] or "test_file_path" not in data[0]:
            print("extracting Junit version")
            junit_version, source_dir, test_source_dir = extract_maven_information()
            if junit_version is None:
                print("could not extract junit version from maven project. Probably is Junit 5\n")
                junit_version = "5.0"
            print(f"Used Junit Version: {junit_version}")

        else :
            junit_version = data[0]["junit_version"]

        print("prepare data")
        for d in tqdm(data):
            if "junit_version" not in d or "test_file_path" not in d:
                d["junit_version"] = junit_version

                if test_source_dir is not None and source_dir is not None:
                    d["test_file_path"] = d["code_file_path"].replace(source_dir.replace("/root/", ""), test_source_dir.replace("/root/", ""))
                    d["test_file_path"] = d["test_file_path"].replace(".java", "Test.java")
                else:
                    d["test_file_path"] = d["code_file_path"].replace(".java", "Test.java")

            if "test_package" not in d:
                d["test_package"] = d["package"]

            # search for junit specific imports   if they are not there add them
            d["test_imports"] = d.get("test_imports", [])

            junit_found = False
            for imp in d["test_imports"]:
                if "junit" in imp:
                    junit_found = True
                    break

            if not junit_found:
                if d["junit_version"].startswith("3"):
                    d["test_imports"].append("import junit.framework.*;\n")
                elif d["junit_version"].startswith("4."):
                    d["test_imports"].append("import org.junit.*;\n")
                    d["test_imports"].append("import static org.junit.Assert.*;\n")
                else:
                    d["test_imports"].append("import org.junit.jupiter.api.*;\n")

        return data


