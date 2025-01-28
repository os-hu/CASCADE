import re

from cascade.analysis.executor.builders.Builder import Builder
from cascade.utils.DockerizedWrapper import DockerizedWrapper


class MavenBuilder(Builder):
    def __init__(self, new_image_name, maven_args, set_up_maven_command, set_up_maven_args, image, timeout=120):
        super().__init__(
            test_pattern = f"echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; timeout {timeout} mvn test {maven_args} -Dtest=\"%t\" -DfailIfNoTests=false > output 2>&1; cat output > out; cat output",

            eval_function = self.eval_function,
            image = new_image_name
        )
        self.old_image_name = image
        self.set_up_maven_args = set_up_maven_args
        self.set_up_maven_command = set_up_maven_command


    def eval_function(self, x):
        """
        The function that has to be given to a builder to evaluate the output of the tests.
        :param x: a string containing the output produced in the docker,
                    which should contain the output of the tests which are then parsed here.
        :return: result, a 2-tuple of
            first a three-tuple of lists of strings,
                the first list contains the ids of the tests that passed,
                the second list contains the ids of the tests that failed,
                the third list contains the ids of the tests that errored
            second a string containing any (compilation) errors that happened during execution or 'None' if none happened
        """
        result = [[],[],[]]
        matches = re.search(r"Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+, Time", x)
        if not matches:
            return ([], [], []), "ERROR: test result pattern not found."
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

        # catch all compilation errors
        comp_matches = re.findall(r'\[ERROR\] COMPILATION ERROR :[\s\S]*?\[INFO\] -*\n(.*?)\[INFO\]', x, re.DOTALL)

        # debugging TODO remove
        with open("/home/kiecketo/tmp/out.txt", "a") as f:
            f.write(f"-------------------\n")
            f.write(x + "\n")
            f.write(str(comp_matches) + "\n")
            f.write(f"-----\n")
            if comp_matches:
                f.write(comp_matches[-1].strip() + "\n")

        if comp_matches:
            comp_errors = comp_matches[-1].strip()
        else:
            comp_errors = None

        return result, comp_errors

    def set_up(self, temp_dir, _, output_path):
        """
        Sets up the environment for execution. Should be called once in the beginning of the Analysis
        :param temp_dir:
        :param output_path:
        :return: The
        """
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "image": self.old_image_name,
            "new_image": self.image,
            "directory": temp_dir,
            "command": f"timeout 120 mvn {self.set_up_maven_command} {self.set_up_maven_args}; RET=$?; rm -rf ../root/*; exit $RET;",
        }
        return wrapper.setup_image(dock_context, output_path)

    def tear_down(self, _):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "new_image": self.image,
        }
        wrapper.remove_image(dock_context)

