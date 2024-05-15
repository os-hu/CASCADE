import ast
import re
import os
import subprocess

from src.analysis.executor.builders.Builder import Builder
from src.utils.DockerizedWrapper import DockerizedWrapper


class MavenBuilder(Builder):
    def __init__(self):
        super().__init__("echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; output=$(mvn test -Drat.skip=true -Dtest=%t | grep -E \"Tests run\" | grep -v in && tail -n 1) && echo $output > out;",
                         self.eval_function,
                         "maven_modified")

    def eval_function(self, x):
        matches = list(map(int, re.findall(r"\d+", x)))
        total_tests = matches[0]
        counter = 0
        result = ([], [], [])
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

    def build(self, temp_dir):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "image": "maven",
            "new_image": "maven_modified",
            "directory": temp_dir,
            "command": "mvn dependency:go-offline; rm -rf ../root/*;",
        }
        wrapper.setup_image(dock_context)


#executor debug an    neuer filter dazu