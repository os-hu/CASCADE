import unittest
from cascade.analysis.executor.UnittestExecutor import UnittestExecutor

class test_UnittestExecutor(unittest.TestCase):
    context = {
        "root_path" : "./resources/python/Test_Project",
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
        "tests": """import unittest
import src.Basic_Calc


class test_Basic_Calc(unittest.TestCase):

    def test_sumgood(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertEqual((3 + 3), c.sum(3, 3))

    def test_sumgood2(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertEqual((4 + 3), c.sum(3, 4))

    def test_sumbad(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertNotEqual(55, c.sum(50, 5))

    def test_sumerror(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertNotEqual(55, src.Basic_Calc.sum(50, 5))
""",
        "new_tests" : """import unittest
import src.Basic_Calc


class test_Basic_Calc(unittest.TestCase):

    def test_sumgood(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertEqual((3 + 3), c.sum(3, 3))

    def test_sumgood2(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertEqual((4 + 3), c.sum(3, 4))

    def test_sumbad(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertNotEqual(55, c.sum(50, 5))

    def test_sumerror(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertNotEqual(55, src.Basic_Calc.sum(50, 5))
""",
        "test_imports": ["import unittest", "import src.Basic_Calc"],
        "test_file_path": "test/test_Basic_Calc.py",
        "testrunner": "unnittest",
    }

    def test_exec_old_old(self):
        executor = UnittestExecutor()
        res = executor.execute("code","tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)


    def test_exec_old_new(self):
        #test for old code and new test
        executor = UnittestExecutor()
        res = executor.execute("code","new_tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)

    def test_exec_new_old(self):
        # test for new code and old test
        executor = UnittestExecutor()
        res = executor.execute("new_code", "tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)


    def test_exec_new_new(self):
        # test for new code and new test
        executor = UnittestExecutor()
        res = executor.execute("new_code", "new_tests", self.context)
        self.assertEqual((['test_sumgood', 'test_sumgood2'], ['test_sumbad'], ['test_sumerror']), res)

