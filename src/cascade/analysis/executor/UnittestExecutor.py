import ast

from cascade.analysis.executor.AnalysisExecutor import AnalysisExecutor, succeeded, failed, errored
from cascade.utils.DockerizedWrapper import DockerizedWrapper
import os
import tempfile
import shutil


class UnittestExecutor(AnalysisExecutor):
    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug

    class ReplaceFunctionBody(ast.NodeTransformer):
        """
        This is used to replace the Body of a fucntion in a file parsed to an AST
        """
        def __init__(self, function_name, new_body):
            self.function_name = function_name
            self.new_body = ast.parse(new_body).body  # Parse the new body into an AST

        def visit_FunctionDef(self, node):
            # Check if the function name matches
            if node.name == self.function_name:
                # Replace the body of the function
                node.body = self.new_body
            # Return the modified node
            return node

    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):

        # copy project
        my_path = os.path.dirname(__file__)

        result = ([], [], [])

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                root_dir = os.path.basename(context["root_path"])
                shutil.copytree(os.path.join(my_path, "..", "..", "..", "resources", "templates" , "PythonTemplate"), temp_dir , dirs_exist_ok=True)
                shutil.copytree(context["root_path"], temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            if code != "code":
                # path to the correct file
                path_to_code = os.path.join(temp_dir, context["code_file_path"])

                with open(path_to_code, "r") as code_file:
                    old_code_file = code_file.read()

                tree = ast.parse(old_code_file)


                # TODO make this handle several functions of te same name in  the same file  ( via contex[parent] or signature )
                transformer = self.ReplaceFunctionBody(context["signature"]["name"], context[code] )
                new_tree = transformer.visit(tree)

                new_code_file = ast.unparse(new_tree)

                with open(path_to_code, "w") as code_file:
                    code_file.write(new_code_file)

            # create and write test into a file"
            with open(os.path.join(temp_dir, "test.py"), "w") as file:
                file.write(context[tests])

            dock_ex = DockerizedWrapper(debug=self.debug)

            dock_context = {
                "image" : "python",
                "directory" : temp_dir,
                "command" : "ls; cat test.py; timeout 30 python3 test-runner.py",
                "eval_command" : "cat out",
                "eval_function" : lambda x : [ast.literal_eval(l) for l in x.split(";")]
            }

            result = dock_ex.execute(dock_context)

        return result

    def set_up(self, context):
        pass

    def tear_down(self, context):
        pass

