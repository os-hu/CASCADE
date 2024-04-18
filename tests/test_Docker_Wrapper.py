import unittest
import os

from src.Dockerized_Wrapper import Dockerized_Wrapper

class test_Docker_Wrapper(unittest.TestCase):

    def test_execute(self):
        wrapper = Dockerized_Wrapper()
        path = os.path.abspath(os.path.join(".", "test_resources", "dockertest"))
        context = dict()
        context["image"] = "ubuntu"
        context["directory"] = path
        context["command"] = "echo hi; ls; bash test.sh"
        context["eval_command"] = "echo 1 2 3"
        context["eval_function"] = lambda x: [[e] for e in x.split()]

        result = wrapper.execute(context)
        succeeded, failed, errored = result

        self.assertEqual(succeeded, ["1"])
        self.assertEqual(failed, ["2"])
        self.assertEqual(errored, ["3"])
