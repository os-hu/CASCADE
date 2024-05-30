import gzip
import json
import os

from cascade.extraction.JsonExtraction import JsonExtraction
import ast
from cascade.extraction.Extraction import Extraction
from cascade.utils.Utils import save_dicts_list_to_json


class HumanEvalExtraction(Extraction):
    """
    An implementation of the abstract "Extraction" class.
    This is designed to extract the Basic 164 functions from the HumanEval dataset provided in its basic json format.
    See extract() method for details.
    """
    def __init__(self):
        super().__init__()

    class AssertTransformer(ast.NodeTransformer):
        """
        this class is used to visit asserts in the test methods and convert them into correspodnign unittest classes.

        it was partially written with the help of chatGPT

        """
        def visit_Assert(self, node):
            # Handle floating-point comparisons: assert abs(expr1 - expr2) < delta
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Lt):
                call_func = node.test.left.func
                if ((isinstance(call_func, ast.Name) and call_func.id == 'abs') or
                        (isinstance(call_func, ast.Attribute) and call_func.attr == 'abs')):
                    left = node.test.left.args[0]  # The expression inside abs()
                    right = node.test.comparators[0]  # The right-hand side of the '<' comparison
                    # Create the assertAlmostEqual call
                    return ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
                                           attr='assertAlmostEqual', ctx=ast.Load()),
                        args=[left, right],
                        keywords=[ast.keyword(arg='delta', value=right)]
                    ))

            # Handle 'assert expression'
            if not isinstance(node.test, ast.UnaryOp):
                return ast.Expr(value=ast.Call(
                    func=ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
                                       attr='assertTrue', ctx=ast.Load()),
                    args=[node.test],
                    keywords=[]
                ))

            # Handle 'assert not expression'
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                return ast.Expr(value=ast.Call(
                    func=ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
                                       attr='assertFalse', ctx=ast.Load()),
                    args=[node.test.operand],
                    keywords=[]
                ))

            return node

    def extract(self, input_path, output_path, print_mode=False) -> list[dict]:
        """
        This method is used to extract the HumanEval Dataset from a json file.
        The format of the json objects in the file should be:

        {

            "task_id": a string, usually: 'HumanEval/xy'
            "prompt": a string containing the generation prompt. usually imports followed
                by the function definition and the docstring
            "entry_point": the starting point for the generation, usually the function name
            "canonical_solution": the body of the function containing a possible solution correct implementation
                of the behavior explained in the docstring
            "test": a test function filled with asserts, called check(candidate) in a string. usually preceded
                by a dictionary called METADATA.
        }
        The output is the dictionary as described in the abstract super class "Extraction"

        It also parses the very simplistic tests from HumaneEval into Python unittest classes.

        :param input_path: should be a path to a file which contains the human eval dataset (or a subset of it.) either
        in json, (jsonl) or a .gz containing a json file
        Can also be a path to a folder containing exactly one file, then this is read in.

        :param output_path: the extracted dataset is saved as a temporary json file called "extracted.json"
        in this specified folder.
        if the path contains a filename (ends in ".json") this name is chosen instead.

        :param print_mode:

        :return: a dictionary
        """

        json_extractor = JsonExtraction()
        extracted = json_extractor.extract(input_path, output_path)
        if extracted:
            return extracted

        if print_mode: print(f"starting to extract from: {input_path}")

        # check if the path is to a file or to a folder
        if os.path.isdir(input_path):
            # List all files in the directory
            files = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]

            # Check if there is exactly one file
            if len(files) == 1:
                file_path = os.path.join(input_path, files[0])

            elif len(files) == 0:
                raise FileNotFoundError("there is no file in this folder")
            else:
                raise FileNotFoundError("there is more than one file in the folder")

        elif os.path.isfile(input_path):
            file_path = input_path

        else:
            raise FileNotFoundError(f"could not find folder or file: {input_path}")

        allowed_extensions = (".json",".jsonl",".gz")
        if not file_path.endswith(allowed_extensions):
            raise FileNotFoundError("found no json or gz file")

        else:
            raw_data = []
            if file_path.endswith(".gz"):
                with gzip.open(file_path, "rt") as file:
                    for line in file:
                        raw_data.append(json.loads(line))

            else:
                with open(file_path, 'r') as file:
                    for line in file:
                        raw_data.append(json.loads(line))

        if print_mode: print(f"extracted {len(raw_data)} entries")

        # handling and extracting
        data = []

        for entry in raw_data:
            # ['task_id', 'prompt', 'entry_point', 'canonical_solution', 'test'])
            temp = {}
            temp["id"] = entry["task_id"]
            func_name = entry["entry_point"]

            # the dict to be extracted
            results = {
                "doc": "",
                "id": int(entry["task_id"][10:]),
                "signature": {
                    "name": func_name,
                    "returns": "",
                    "params": []
                },
                "language": "python",
                "parent": {
                    "imports": [],
                    "other_methods": []
                },
                "code": entry["canonical_solution"],
                "called_functions": "",
                "tests": "",
                "testrunner":  "unittest"
            }

            complete_code = entry["prompt"] + entry["canonical_solution"]
            tree = ast.parse(complete_code)

            # collect ALL imports that could be needed for any part of the code
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_line = ast.unparse(node).strip()
                    results["parent"]["imports"].append(import_line)

                elif isinstance(node, ast.FunctionDef):
                    if node.name == func_name:
                        # found the interesting method.
                        # documentation
                        results["doc"] = ast.get_docstring(node) #includes usage examples.

                        # Parameters and types
                        for param in node.args.args:
                            param_name = str(param.arg)
                            if param.annotation:
                                param = f"{param_name}: {ast.unparse(param.annotation).strip()}"
                            else:
                                param = param_name
                            results["signature"]["params"].append(param)

                        # Return Type
                        if node.returns:
                            results["signature"]["returns"] = ast.unparse(node.returns).strip()

                    else:
                        # TODO Parse these into usable functions each as a dict
                        results["parent"]["other_methods"].append(ast.unparse(node))

            base_tests = "import unittest\n\nclass test_{name}(unittest.TestCase):\n  def test_1(self):\n{test_method}\n\nif __name__ == '__main__':\n    unittest.main()"


            # findign and converting text


            raw_test = entry["test"]#.replace("candidate" , func_name)
            # Parse the source code into an AST
            tree = ast.parse(raw_test)

            # transform asset statements
            raw_tests_unittest = ast.unparse(self.AssertTransformer().visit(tree))

            unindented_tests = raw_tests_unittest.replace("def check(candidate)" , f"def test_{func_name}(self)").replace("candidate" , func_name)
            indented_tests = "\n".join("    " + line for line in unindented_tests.splitlines())

            results["tests"] = f"import unittest\nfrom func import *\n\nclass test_func(unittest.TestCase):\n{indented_tests}"

            data.append(results)

        if print_mode: print(f"formated {len(data)} entries")

        if output_path is None or output_path == "":
            output_path = ""

        output_file_path = output_path + "/HumanEval_extracted.json"
        try:
            # save the extracted data
            save_dicts_list_to_json(data, output_file_path, create_folder=True, override=True)
            if print_mode:
                print(f"saved data to: {output_file_path}")
        except:
            if print_mode:
                print(f"failed to save to: {output_file_path}")

        return data
