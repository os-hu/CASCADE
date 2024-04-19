import ast
import sys

from src.abstract_classes.Analysis_Executor import Analysis_Executor, succeeded, failed, errored
from src.implementations.analysis.analysis_executor.Unittest_Executor import Unittest_Executor

import os
import tempfile
import shutil



class HumanEval_Executor(Analysis_Executor):
    def __init__(self, debug=False):
        self.debug = debug


    def build_code_file(self, context) -> str:
        imports = "\n".join(context["parent"]["imports"])
        imports = imports + "\n"
        imports = imports + "\n".join(context["parent"]["other_methods"])

        name = context["signature"]["name"]
        para = context["signature"]["params"]

        if len(para) > 1:
            param_string = ", ".join(para)
        else:
            param_string = para[0] if len(para) == 1 else ""

        returns = context["signature"]["returns"]
        signature = f"def {name}({param_string})" + (" -> " + returns if returns else "") + ":"

        doc = f"\"\"\"\n{context['doc']}\n\"\"\""
        doc = "\n".join("    "+line for line in doc.splitlines())

        body = context["code"]

        full_func = "\n".join([imports, "\n" , signature, doc, "", body])

        if self.debug:
            print("build function: " , full_func)

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
