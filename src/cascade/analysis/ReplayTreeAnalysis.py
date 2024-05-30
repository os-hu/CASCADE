import os

from tqdm import tqdm

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.visualizer.Visualization import Visualization

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, log


class ReplayTreeAnalysis(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization, debug=0):
        super().__init__(generator, executor, visualizer)
        self.debug = debug
        self.visualizer.logger = "tqdm"

    def analyse(self, data: list, output_path):
        """
        TODO
        :param output_path:
        :param data:
        :return:
        """

        input("""
        This is not a proper analysis.
        It will not generate or execute any code or tests. 
        it is just used to replay the tree analysis of an already existing analyzed file 
        
        If you want to run a proper analysis run the TreeAnalysis instead. 
        Look into the README.md for how to do that but note that you would need you own openai API key.
        
        press enter to continue
        """)

        # generated artifacts for the same dataset can be saved to avoid repeated generation of code and tests.
        temp_data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
        if not temp_data:
            raise Exception("No analyzed.json file found in", output_path)

        del data
        data = temp_data

        #  loop through data
        for d in tqdm(data):
            if self.debug >= 2:
                self.visualizer.visualize(data, output_path)

            if "results" not in d:
                continue

            # Phase 1  code + tests: --------------------------------------
            if "id" in d and d["id"] != "":
                log(d["id"], logger="tqdm")
            else:
                log(d["signature"]["name"], logger="tqdm")
            log("    Level 1", logger="tqdm")


            if "(code, tests)" not in d["results"]:
                continue
            res1 = d["results"]["(code, tests)"]

            if self.should_skip(res1, False):
                continue
            del res1


            # Level 2   code + new_tests: ---------------------------------
            log("    Level 2", logger="tqdm")

            if "(code, new_tests)" not in d["results"]:
                continue

            res2 = d["results"]["(code, new_tests)"]

            if self.should_skip(res2, True):
                continue
            del res2


            # Level 3   new_code + new_tests: ---------------------------------
            log("    Level 3", logger="tqdm")


            if "(new_code, new_tests)" not in d["results"]:
                continue

            res3 = d["results"]["(new_code, new_tests)"]

            if self.should_skip(res3, False):
                continue
            del res3


            # Level 4   new_code + tests: ---------------------------------
            log("    Level 4", logger="tqdm")

            if "(new_code, tests)" not in d["results"]:
                continue

            res4 = d["results"]["(new_code, tests)"]

            if self.should_skip(res4, True):
                continue
            del res4

        self.visualizer.visualize(data, output_path, full=True)

    def should_skip(self, res, skip_on_passed):
        if res[0] == [] and res[1] == []:
            if self.debug >= 1:
                log("        Error", logger="tqdm")
            # error
            return True
        elif res[1] == [] and res[2] == []:
            if self.debug >= 1:
                log("        Passed", logger="tqdm")
            # if no errors or failures  then passed
            return skip_on_passed
        else:
            if self.debug >= 1:
                log("        Failed", logger="tqdm")
            # failed
            return not skip_on_passed
