import unittest
import os

from cascade.utils.DockerizedWrapper import DockerizedWrapper


class TestDockerizedWrapper(unittest.TestCase):

    def test_execute(self):
        wrapper = DockerizedWrapper()
        path = os.path.abspath(os.path.join(".", "resources", "dockertest"))
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
