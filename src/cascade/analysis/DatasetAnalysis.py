import os
from doctest import debug

from tqdm import tqdm

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.visualizer.Visualization import Visualization

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, log, save_dicts_list_to_json


class DatasetAnalysis(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization, regenerate=False, reexecute=False, debug=0, step_size=1):
        super().__init__(generator, executor, visualizer)
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.visualizer.logger = "tqdm"




    def analyse(self, data: list, input_path, output_path):
        """
        this is the specific analysis for the dataset benchmark. it only executes level 2 and 3 of a normal tree analysis.
        it does not visualize anything. it does however safe the results in a file called result_CASCADE.txt
        :param input_path:
        """
        # print("Set up started")
        # if not self.executor.set_up(data, output_path) and self.die_if_setup_fails:
        #     print("Set up failed")
        #     return
        # print("Set up finished")

        output = ""

        # load data for this specific run.
        data = load_json_from_path(os.path.join(output_path, "analyzed.json"))

        d = data[0]

        print(f"Starting analysis of {d['signature']['name']}")

        d["results"] = {}

        print("generate new tests")
        new_tests, response = self.generator.generate_tests(d, output_path)
        d["new_tests"] = new_tests
        print("execute new tests")

        # only executes level 2 and 3
        res2 = list(self.executor.execute("code", "new_tests", d, input_path, output_path))

        # check if it passed failed or errored
        evaluated = self.evaluate(res2)
        if evaluated >= 0:
            output += "False"
            if self.debug >= 1:
                output += ", error in layer 2: code, new_tests" if evaluated == 0 else ", pass in layer 2: code, new_tests"

        else:
            # generate new code
            new_code, response = self.generator.generate_code(d, output_path)

            d["new_code"] = new_code

            # execute new code
            res3 = list(self.executor.execute("new_code", "new_tests", d, input_path, output_path))
            evaluated = self.evaluate(res3)
            if evaluated <= 0:
                output += "False"
                if self.debug >= 1:
                    output += ", error in layer 3: new_code, new_tests" if evaluated == 0 else ", fail in layer 3: new_code, new_tests"

            else:
                output += "True"

        with open("result.txt", "w") as f:
            f.write(output)
        if self.debug >= 1:
            print("result:" , output)


    def evaluate(self, res):
        if res[0] == [] and res[1] == []:
            if self.debug >= 1:
                log("        Error", logger="tqdm")
            # error
            return 0
        elif res[1] == [] and res[2] == []:
            if self.debug >= 1:
                log("        Passed", logger="tqdm")
            # if no errors or failures  then passed
            return 1
        else:
            if self.debug >= 1:
                log("        Failed", logger="tqdm")
            # failed
            return -1
