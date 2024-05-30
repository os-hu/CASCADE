import re

from cascade.analysis.executor.builders.Builder import Builder
from cascade.utils.DockerizedWrapper import DockerizedWrapper


class MavenBuilder(Builder):
    def __init__(self,
                 new_image_name,
                 maven_args,
                 set_up_maven_command,
                 set_up_maven_args,
                 image):
        super().__init__(f"echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; timeout 120 mvn test {maven_args} -Dtest=\"%t\" -DfailIfNoTests=false 2>&1 > output; cat output > out; cat output",
                         self.eval_function, new_image_name)
        self.old_image_name = image
        self.set_up_maven_args = set_up_maven_args
        self.set_up_maven_command = set_up_maven_command


    def eval_function(self, x):
        """
        The function that has to be given to the builder to evaluate the output of the tests
        :param x: a string containing the output produced in the docker,
                    which should contain the output of the tests which are then parsed here.
        :return: result a tuple of three lists of strings,
            the first list contains the ids of the tests that passed,
            the second list contains the ids of the tests that failed,
            the third list contains the ids of the tests that errored
        """
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
            "image": self.old_image_name,
            "new_image": self.image,
            "directory": temp_dir,
            "command": f"mvn {self.set_up_maven_command} {self.set_up_maven_args}; rm -rf ../root/*;",
        }
        wrapper.setup_image(dock_context)

    def tear_down(self, _):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "new_image": self.image,
        }
        wrapper.remove_image(dock_context)

