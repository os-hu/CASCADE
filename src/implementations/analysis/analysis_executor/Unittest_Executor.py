import ast

from src.abstract_classes.Analysis_Executor import Analysis_Executor, succeeded, failed, errored
from src.Dockerized_Wrapper import Dockerized_Wrapper
import os
import tempfile
import shutil

class Unittest_Executor(Analysis_Executor):
    def __init__(self):
        pass

    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):

        # copy project
        my_path = os.path.dirname(__file__)

        result = ([], [], [])

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                root_dir = os.path.basename(context["root_path"])
                shutil.copytree(os.path.join(my_path, "..", "..", "..", "..", "resources", "templates" , "PythonTemplate"), temp_dir , dirs_exist_ok=True)
                shutil.copytree(context["root_path"], temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            if code != "code":
                # TODO if code is not old code replace"
                new_code = context[code]


            # create and write test into a file"
            with open(os.path.join(temp_dir, "test.py"), "w") as file:
                file.write(context[tests])


            dock_ex = Dockerized_Wrapper(debug=False)

            dock_context = {
                "image" : "python",
                "directory" : temp_dir,
                "command" : "ls; cat test.py; python3 test-runner.py",
                "eval_command" : "cat out",
                "eval_function" : lambda x : [ast.literal_eval(l) for l in x.split(";")]
            }

            result = dock_ex.execute("","",dock_context)

        return result

