import os

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




    def analyse(self, data: list, output_path):
        """
        TODO
        :param output_path:
        :param data:
        :return:
        """

        # load data for this specific run.
        temp_data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
        if temp_data:
            del data
            data = temp_data

        d = data[0]

        print(f"Starting analysis of {d['signature']['name']}")

        d["results"] = {}

        print("generate new tests")
        new_tests, response = self.generator.generate_tests(d, output_path)
        d["new_tests"] = new_tests

        print("execute new tests")

        res2 = self.executor.execute("code", "new_tests", d, output_path)
        # TODO what if this does not work?
        d["results"]["(code, new_tests)"] = list(res2)

        # save
        save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))


        # generate new code
        new_code, response = self.generator.generate_code(d, output_path)

        d["new_code"] = new_code

        # execute new code
        res3 = self.executor.execute("new_code", "new_tests", d, output_path)
        d["results"]["(new_code, new_tests)"] = list(res3)



        save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))

        # what does that do`
        self.executor.tear_down(data)
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
