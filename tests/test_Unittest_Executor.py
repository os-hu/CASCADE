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
            "imports": ["math"],
            "other_methods": ["mult", "div"],
            "variables": ["pi", ""],
            # "generics" : ""
        },
        "code": "        return a+b",
        "new_code" : "return math.fsum([a, b])",
        "code_file_path": "src/Basic_Calc.py",
        "called_functions": [],
        "tests": "",
        "new_tests" : "",
        "test_imports": ["import unittest", "import src.Basic_Calc"],
        "test_file_path": "test/test_Basic_Calc.py",
        "testrunner": "unnittest",
    }


    def setUp(self):
        # TODO pfad relativ machen
        with open(
                "/home/kiecketo/PycharmProjects/CASCADE/tests/test_resources/python/Test_Project/test/test_Basic_Calc.py",
                "r") as file:
            self.context["tests"] = file.read()

    def test_exec_old_old(self):
        executor = Unittest_Executor()
        res = executor.execute("code","tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)


    def test_exec_old_new(self):
        #test for old code and new test
        executor = Unittest_Executor(debug=True)
        res = executor.execute("code","new_tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)

    def test_exec_new_old(self):
        # test for new code and old test
        executor = Unittest_Executor()
        res = executor.execute("new_code", "tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)


    def test_exec_new_new(self):
        # test for new code and new test
        executor = Unittest_Executor()
        res = executor.execute("new_code", "new_tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)

