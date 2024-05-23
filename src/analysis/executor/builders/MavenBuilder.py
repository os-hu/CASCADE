import ast
import re
import os
import subprocess

from src.analysis.executor.builders.Builder import Builder
from src.utils.DockerizedWrapper import DockerizedWrapper


class MavenBuilder(Builder):
    def __init__(self, new_image_name, maven_args=""):
        super().__init__(f"echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; timeout 120 mvn test {maven_args} -Dtest=\"%t\" -DfailIfNoTests=false 2>&1 > output; cat output > out; cat output",
                         self.eval_function,
                         new_image_name)
        self.new_image_name = new_image_name

    def eval_function(self, x):
        matches = re.search(r"Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+, Time", x)
        result = ([], [], [])
        if not matches:
            return result
        matched_line = matches[0]
        matches = list(map(int, re.findall(r"\d+", matched_line)))
        total_tests = matches[0]
        counter = 0
        for match in range(matches[1]):
            result[1].append(str(counter))
            counter += 1
        for match in range(matches[2]):
            # there is a fourth option namely skipped tests  matches[3]  which we ignore
            result[2].append(str(counter))
            counter += 1
        for match in range(counter, total_tests):
            result[0].append(str(counter))
            counter += 1
        return result

    def set_up(self, temp_dir, _):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "image": "maven",
            "new_image": self.new_image_name,
            "directory": temp_dir,
            "command": "mvn dependency:go-offline; rm -rf ../root/*;",
        }
        wrapper.setup_image(dock_context)

    def tear_down(self, _):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "new_image": self.new_image_name,
        }
        wrapper.remove_image(dock_context)

#executor debug an    neuer filter dazu