import json
import subprocess

from cascade.analysis.executor.AnalysisExecutor import AnalysisExecutor, succeeded, failed, errored
from cascade.utils.DockerizedWrapper import DockerizedWrapper

import os
import tempfile
import shutil


class JavaExecutor(AnalysisExecutor):
    def __init__(self, debug=False, builder=None):
        super().__init__()
        self.debug = debug
        self.builder = builder

    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):
        result = ([], [], [])

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.copytree(context["root_path"], temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            entry = os.path.join(temp_dir, "entry.json")
            with open(entry, "w") as json_entry:
                json.dump(context, json_entry)
            my_path = os.path.dirname(__file__)
            p = subprocess.run(
                ["java", "-jar", os.path.join(my_path, "..", "..", "..", "resources", "tools", "JavaModifier.jar"),
                 temp_dir,
                 entry,
                 code,
                 tests],
                capture_output=True,
                text=True
            )

            os.remove(entry)

            if p.stderr:
                if self.debug:
                    print(p.stdout)
                    print(p.stderr)
                return [], [], []

            if self.debug:
                print(p.stdout)

            dock_ex = DockerizedWrapper(debug=self.debug)

            test_class_name = (self.builder.test_pattern
                               .replace('%t', context['test_file_path'].split('/')[-1].split('.')[0]))
            dock_context = {
                "image" : self.builder.image,
                "directory" : temp_dir,
                "command" : f"ls;"
                            f"{test_class_name}",
                "eval_command" : "cat out",
                "eval_function" : self.builder.eval_function
            }

            result = dock_ex.execute(dock_context)

        return result

    def set_up(self, data):
        context = data[0]

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.copytree(context["root_path"], temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            if self.builder:
                self.builder.set_up(temp_dir, context)

    def tear_down(self, data):
        context = data[0]

        if self.builder:
            self.builder.tear_down(context)

