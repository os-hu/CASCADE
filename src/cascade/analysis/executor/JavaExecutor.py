import json
import subprocess

from cascade.analysis.executor.AnalysisExecutor import AnalysisExecutor, succeeded, failed, errored
from cascade.utils.DockerizedWrapper import DockerizedWrapper

import re
import os
import tempfile
import shutil


class JavaExecutor(AnalysisExecutor):
    def __init__(self, debug=False, builder=None):
        super().__init__()
        self.debug = debug
        self.builder = builder

    def execute(self, code: str, tests: str, context: dict, input_path, output_path) -> (succeeded, failed, errored):
        result = ([],[],[])
        errors = None

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.copytree(input_path, temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            entry = os.path.join(temp_dir, "entry.json")
            with open(entry, "w") as json_entry:
                json.dump(context, json_entry)
            my_path = os.path.dirname(__file__)
            p = subprocess.run(
                ["java", "-jar", os.path.join(my_path, "..", "..", "resources", "tools", "JavaExtractor.jar"),
                 "mod",
                 temp_dir,
                 entry,
                 code,
                 tests],
                capture_output=True,
                text=True
            )

            os.remove(entry)

            with open(os.path.join(output_path, "log.txt"), "a") as file:
                file.write(str(context["id"]) + "\n")
                file.write(p.stdout + "\n")
                file.write(p.stderr + "\n")

            if p.stderr:
                if self.debug:
                    print(p.stdout)
                    print(p.stderr)
                return ([],[],[]), None

            if self.debug:
                print(p.stdout)

            dock_ex = DockerizedWrapper(debug=self.debug)

            #test_class_name = (self.builder.test_pattern.replace('%t', context['test_package'] + "." + context['test_file_path'].split('/')[-1].split('.')[0]))
            #debuggin verison TODO remove and uncommnet thing above
            test_command = (self.builder.test_pattern.replace('%t', "THIS_IS_A_UNIQUE_NAME_Test"))

            dock_context = {
                "image" : self.builder.image,
                "directory" : temp_dir,
                "command" : f"ls; cat -n {context['code_file_path']}; cat -n {context['test_file_path']};"
                            f"{test_command}",
                "eval_command" : "cat out",
                "eval_function" : self.builder.eval_function
            }

            result, errors = dock_ex.execute(dock_context, output_path)

        return result, errors


    def set_up(self, data, input_path, output_path):
        context = data[0]

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.copytree(input_path, temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            if self.builder:
                return self.builder.set_up(temp_dir, input_path, input_path)
        return False

    def tear_down(self, data):
        context = data[0]

        if self.builder:
            self.builder.tear_down(context)

