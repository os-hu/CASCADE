from cascade.analysis.executor.AnalysisExecutor import succeeded, failed, errored
from cascade.analysis.executor.UnittestExecutor import UnittestExecutor
from cascade.utils.PythonUtils import build_signature

import os
import tempfile


class HumanEvalExecutor(UnittestExecutor):
    def __init__(self, debug=False):
        super().__init__(debug)

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
            with open(os.path.join(temp_dir, "func.py"), "w") as file:
                file.write(self.build_code_file(context))

            context["root_path"] = temp_dir

            try:
                result = super().execute(code, tests, context)
            except Exception as e:
                if self.debug:
                    print("failed to execute:" , e)
                result = ([], [], [])

        return result
