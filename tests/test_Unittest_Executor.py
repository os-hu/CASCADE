import unittest
from src.implementations.analysis.analysis_executor.Unittest_Executor import Unittest_Executor

class MyTestCase(unittest.TestCase):
    context = {
        "root_path" : "/home/kiecketo/PycharmProjects/CASCADE/tests/test_resources/python/Test_Project",
        "doc": "not relevant",
        "signature": {
            "name": "sum",
            "returns": "int",
            "params": "self, a : int , b : int",
            #"annotations": "",
            # "generics" : ""
        },
        # "language" : "python"
        "parent": {
            "name": "Basic_Calc",
            "doc": """this is a parent class""",
            "imports": "math",
            "other_methods": ["mult", "div"],
            "variables": ["pi", ""],
            # "generics" : ""
        },
        "code": "        return a+b",
        "new_code" : "        return math.sum(a, b)",
        "code_file_path": "src.Basic_Calc",
        "called_functions": [],
        "tests": "",
        "test_imports": ["import unittest", "import src.Basic_Calc"],
        "test_file_path": "test.test_Basic_Calc",
        "testrunner": "unnittest",
    }

    with open("/home/kiecketo/PycharmProjects/CASCADE/tests/test_resources/python/Test_Project/test/test_Basic_Calc.py", "r") as file:
        context["tests"] = file.read()

    def test_exec(self):
        executor = Unittest_Executor()
        res = executor.execute("code","tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)

