import sys
import os
import gzip
import json
from src import Utils
import re
import ast

from src.abstract_classes.Extraction import Extraction
class Human_Eval_Basic_Extraction(Extraction):
    """
    An implementation of the abstract "Extraction" class.
    This is designed to extract the Basic 164 functions from the HumanEval dataset provided in its basic json format.
    See extract() method for details.
    """
    def __init__(self):
        pass

    class AssertVisitor(ast.NodeVisitor):
        """
        the ast class that is needed to extract the asserts statements in the humaneval dataset and transform them into unitteststyle
        """
        all_replacements = []
        def visit_Assert(self, node):
            # This method is called for every assert statement in the AST
            msg = self.get_assert_message(node)
            suggested_replacement = self.suggest_unittest_assert(node)

            #print(f"Found an assert statement: {ast.unparse(node)}\n Suggested replacement: {suggested_replacement}")

            replacement = suggested_replacement[:-1] + f", msg=({msg}))" if msg else suggested_replacement
            self.all_replacements.append((ast.unparse(node), replacement))

        def get_assert_message(self, node):
            # Extracts the message from the assert, if present
            return ast.unparse(node.msg) if node.msg else None

        def suggest_unittest_assert(self, node):
            # Generates a possible unittest equivalent of the assert statement
            # Handle the case where the test involves a comparison
            if isinstance(node.test, ast.Compare):
                left = ast.unparse(node.test.left)
                right = ast.unparse(node.test.comparators[0])

                if len(node.test.ops) == 1:
                    if isinstance(node.test.ops[0], ast.Eq):
                        return f"self.assertEqual({left}, {right})"
                    elif isinstance(node.test.ops[0], ast.NotEq):
                        return f"self.assertNotEqual({left}, {right})"
                    elif isinstance(node.test.ops[0], ast.Lt):
                        return f"self.assertLess({left}, {right})"
                    elif isinstance(node.test.ops[0], ast.LtE):
                        return f"self.assertLessEqual({left}, {right})"
                    elif isinstance(node.test.ops[0], ast.Gt):
                        return f"self.assertGreater({left}, {right})"
                    elif isinstance(node.test.ops[0], ast.GtE):
                        return f"self.assertGreaterEqual({left}, {right})"

            # Handle calls to abs() and math.fabs() for "close enough" comparisons
            if (isinstance(node.test, ast.Call) and
                    ((isinstance(node.test.func, ast.Name) and node.test.func.id == 'abs') or
                     (isinstance(node.test.func, ast.Attribute) and node.test.func.attr == 'fabs'))):
                # Assuming there's a comparison against a small value to signify "almost equal"
                if len(node.test.args) == 1:
                    arg = ast.unparse(node.test.args[0])
                    return f"self.assertAlmostEqual({arg}, 0, delta=1e-6)"

            # Default case for truth value testing
            return f"self.assertTrue({ast.unparse(node.test)})"



    def extract(self, input_path, output_path, print_mode=False) -> dict:
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
        # TODO read in all files instead?

        :param output_path: the extracted dataset is saved as a temporary json file called "extracted.json"
        in this specified folder.
        if the path contains a filename (ends in ".json") this name is chosen instead.

        :param print_mode:

        :return: a dictionary
        """


        # TODO should this first part go into the Utils load_json function?
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
            raise FileNotFoundError(f"could not find folder or file {input_path}")

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

        # save the extracted dictionaries
        # TODO check the output_path if it is ok.
        #output_file_path = output_path + "/basic_extracted.json"
        #Utils.save_dicts_list_to_json(data, output_file_path, create_folder=True, override=True)
        #if printmode: print(f"saved to: {output_file_path}")

        # handling and extracting.
        data = []
        for entry in raw_data:
            # ['task_id', 'prompt', 'entry_point', 'canonical_solution', 'test'])
            temp = {}
            # id
            temp["id"] = entry["task_id"]
            prompt = entry["prompt"]

            func_name = entry["entry_point"]

            complete_code = entry["prompt"] + entry["canonical_solution"]

            tree = ast.parse(complete_code)

            # the dict to be extracted
            # TODO         results = {
            #                 "code": "",
            #                 "tests": "",
            #                 "test_imports": "",
            #             }
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
                "code": "",
                "called_functions": "",
                "tests": "",
                "test_imports": "",
                "testrunner":  "unittest"
            }

            # collect ALL imports that could be needed for any part of the code
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_line = ast.unparse(node).strip()
                    results["parent"]["imports"].append(import_line)

                elif isinstance(node, ast.FunctionDef):
                    if node.name == func_name:
                        # found the interesting method.
                        # documentation
                        results["doc"] = ast.get_docstring(node) #includes usage examples. TODO heuristic for getting rid of them?

                        # Parameters and types
                        for param in node.args.args:
                            param_name = str(param.arg)
                            if param.annotation:
                                param = f"{param_name}: {ast.unparse(param.annotation).strip()}"
                            results["signature"]["params"].append(param)

                        # Return Type
                        if node.returns:
                            results["signature"]["returns"] = ast.unparse(node.returns).strip()

                        # Body
                        #results["code"] = ast.unparse(node.body).strip()
                        #print(results["doc"])
                        #print(".....")
                        #print(results["code"])
                        #p#rint("-----------")

                    else:
                        results["parent"]["other_methods"] = ast.unparse(node)

            # test. TODO for now i will just put all asserts into one testcase.
            # TODO do we need that last part?
            base_tests = "import unittest\n\nclass test_{name}(unittest.TestCase):\n  def test_1(self):\n{test_method}\n\nif __name__ == '__main__':\n    unittest.main()"


            # findign and converting text


            raw_test = entry["test"]#.replace("candidate" , func_name)

            # Parse the tests into an AST
            parsed_code = ast.parse(entry["test"])

            # Parse the given source code into an AST
            tree = ast.parse(raw_test)
            # Create an instance of our visitor and walk the AST
            visitor = self.AssertVisitor()
            visitor.visit(tree)
            for replacement in visitor.all_replacements:
                raw_test = raw_test.replace(*replacement)

            print("-----------")
            print(raw_test)
            #print(visitor.all_replacements)
            #print("----------")


            # results["tests"] =
            #tests = base_tests.format(name=func_name, test_method="hi")
            #print(tests)
            #print("---------------------")

            # for the tests. do ast walk  check if the fucntion is called  "check"
            # then parse the content of that fucntion  somehow.....
            #check for imports?



        #sys.exit(1)
