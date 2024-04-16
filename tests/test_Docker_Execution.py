import unittest
import os

from src.implementations.analysis.analysis_executor.Dockerized_Executor import Dockerized_Executor

class test_Docker_Execution(unittest.TestCase):

    def test_execute(self):
        executor = Dockerized_Executor()
        path = os.path.abspath(os.path.join(".", "test_resources", "dockertest"))
        context = dict()
        context["image"] = "ubuntu"
        context["directory"] = path
        context["command"] = "cd dockertest; bash test.sh"
        context["eval_command"] = "echo 1 2 3"
        context["eval_function"] = lambda x: [[str(e, "utf-8")] for e in x.split()]

        result = executor.execute("", "", context)
        succeeded, failed, errored = result

        self.assertEqual(succeeded, ["1"])
        self.assertEqual(failed, ["2"])
        self.assertEqual(errored, ["3"])
