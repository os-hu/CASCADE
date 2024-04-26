import ast
import json
import sys
import subprocess

from src.abstract_classes.Analysis_Executor import Analysis_Executor, succeeded, failed, errored
from src.Dockerized_Wrapper import Dockerized_Wrapper
import os
import tempfile
import shutil

class Java_Executor(Analysis_Executor):
    def __init__(self, debug=False, builder=None):
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

            my_path = os.path.dirname(__file__)
            p = subprocess.run(
                ["java", "-jar", os.path.join(my_path, "..", "..", "..", "..", "resources", "tools", "JavaModifier.jar"),
                 temp_dir,
                 json.dumps(context),
                 code,
                 tests],
                capture_output=True,
                text=True
            )
            if self.debug:
                print(p.stdout)

            if self.builder:
                self.builder.build(temp_dir)
            #p = subprocess.run(f"mvn dependency:copy-dependencies {os.path.join(temp_dir, 'pom.xml')}".split())

            dock_ex = Dockerized_Wrapper(debug=self.debug)

            dock_context = {
                "image" : "openjdk",
                "directory" : temp_dir,
                "command" : f"ls; cat {context['code_file_path']}; echo {context['code_file_path']}; cat {context['test_file_path']}; echo {context['test_file_path']};", #TODO junit runner
                "eval_command" : "cat out",
                "eval_function" : lambda x: [ast.literal_eval(l) for l in x.split(";")]
            }

            result = dock_ex.execute(dock_context)

        return result
