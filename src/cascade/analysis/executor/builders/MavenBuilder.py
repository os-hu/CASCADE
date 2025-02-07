import re

from cascade.analysis.executor.builders.Builder import Builder
from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class MavenBuilder(Builder):
    def __init__(self, new_image_name, maven_args, set_up_maven_command, set_up_maven_args, image, timeout=120):
        super().__init__(
            test_pattern = f"echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; timeout {timeout} mvn test {maven_args} -Dtest=\"%t\" -DfailIfNoTests=false -Dsurefire.reportsDirectory=target/surefire-reports > output 2>&1; cat output > out; cat target/surefire-reports/TEST-*.xml >> out; cat output",

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

        # First Catch Compilation Errors
        comp_matches = re.findall(r'\[ERROR\] COMPILATION ERROR :[\s\S]*?\[INFO\] -*\n(.*?)\[INFO\]', x, re.DOTALL)

        if comp_matches:
            comp_errors = comp_matches[-1].strip()
        else:
            comp_errors = None

        test_overview_matches = re.search(r"Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+, Time", x)
        if not test_overview_matches:
            return ([], [], []), comp_errors
        matched_line = test_overview_matches[0]


        run_fail_err_skip = list(map(int, re.findall(r"\d+", matched_line)))
        total_tests = run_fail_err_skip[0]

        xml_blocks = re.findall(r'(<\?xml.*?</testsuite>)', x, re.DOTALL)
        print(xml_blocks)

        # results = {}
        # for block in xml_blocks:
        #     try:
        #         root = ET.fromstring(block)
        #     except ET.ParseError as e:
        #         continue
        #     # Get the test class name (usually in the 'name' attribute)
        #     test_class = root.attrib.get('name', 'unknown')
        #     # Get counts for failures and errors (if they are present)
        #     failures = int(root.attrib.get('failures', '0'))
        #     errors = int(root.attrib.get('errors', '0'))
        #     # Determine the status: passed if both failures and errors are zero.
        #     if failures > 0 or errors > 0:
        #         results[test_class] = 'failed'
        #     else:
        #         results[test_class] = 'passed'


        # counter = 0
        # for match in range(matches[1]):
        #     result[1].append(str(counter))
        #     counter += 1
        # for match in range(matches[2]):
        #     # there is a fourth option namely skipped tests  matches[3]  which we ignore
        #     result[2].append(str(counter))
        #     counter += 1
        # for match in range(counter, total_tests):
        #     result[0].append(str(counter))
        #     counter += 1
        exit()

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

