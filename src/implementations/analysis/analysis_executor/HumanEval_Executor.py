from src.abstract_classes.Analysis_Executor import Analysis_Executor, succeeded, failed, errored
from src.implementations.analysis.analysis_executor.Unittest_Executor import Unittest_Executor
from src.utils.Python_Utils import build_signature

import os
import tempfile
import shutil



class HumanEval_Executor(Analysis_Executor):
    def __init__(self, debug=False):
        self.debug = debug


    def build_code_file(self, context) -> str:
        """
        TODO this
        :param context:
        :return:
        """
        sig_and_doc = build_signature(context, doc=True)

        body = context["code"]
        full_func = sig_and_doc + "\n" + body

        if self.debug:
            print("build function: ", full_func)

        return full_func


    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):
        result = ([], [], [])

        with tempfile.TemporaryDirectory() as temp_dir:
            context["code_file_path"] = "func.py"

            # write the function to a single file just containing it.
            with open(os.path.join(temp_dir , "func.py"), "w") as file:
                file.write(self.build_code_file(context))

            context["root_path"] = temp_dir

            unittest_executor = Unittest_Executor(debug=self.debug)
            result = unittest_executor.execute(code, tests, context)

        return result
