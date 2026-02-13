import re
from cascade.analysis.executor.ExecutionResults import ExecutionResults
from cascade.analysis.executor.builders.Builder import Builder
from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class MavenBuilder(Builder):
    def __init__(self, new_image_name, maven_args, set_up_maven_command, set_up_maven_args, image, timeout=300):
        super().__init__(
            #test_pattern = f"echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; timeout {timeout} mvn test {maven_args} -Dtest=\"%t\" -DfailIfNoTests=false -Dsurefire.reportsDirectory=target/surefire-reports > output 2>&1; cat output > out; cat target/surefire-reports/TEST-*.xml >> out; cat output",

            test_pattern = (f"echo \"[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\" > out; "
                            f"timeout {timeout} mvn clean test {maven_args} -Dtest=\"%t\" -DfailIfNoTests=false "
                            f"-Dsurefire.reportsDirectory=target/surefire-reports > output 2>&1; status=$?; cat output > out; "
                            f"find . -path \"*/target/surefire-reports/TEST-*.xml\" -type f "
                            f"-exec cat {{}} \\; >> out; echo \"[INFO] Exit code: $status\" >> out;"
                            f"cat output"
                            ),

            eval_function = self.eval_function,
            image = new_image_name
        )
        self.old_image_name = image
        self.set_up_maven_args = set_up_maven_args
        self.set_up_maven_command = set_up_maven_command


    def eval_function(self, x):
        """
        An implementation of the function that has to be given to a builder to evaluate the output of the tests.
        :param x: a string containing the output produced in the docker,
                    which should contain the output of the tests which are then parsed here.
        :return: result, a class of TODO ...
            first a three-tuple of lists of strings,
                the first list contains the names of the tests that passed,
                the second list contains the names of the tests that failed,
                the third list contains the names of the tests that errored
            second a string containing any (compilation) errors that happened during execution or 'None' if none occurred
        """
        results = ExecutionResults()
        results.parsed_file = x

        # First Catch Compilation Errors
        comp_matches = re.findall(r'\[ERROR\] COMPILATION ERROR :[\s\S]*?\[INFO\] -*\n(.*?)\[INFO\]', x, re.DOTALL)

        if comp_matches:
            results.comp_error_matches = comp_matches
            results.comp_errors = comp_matches[-1].strip()

        # get general test results
        test_overview_matches = re.search(r"Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+, Time", x)
        results.test_overview_matches = test_overview_matches

        if not test_overview_matches:
            return results

        matched_line = test_overview_matches[0]
        run_fail_err_skip = list(map(int, re.findall(r"\d+", matched_line)))
        total_tests = run_fail_err_skip[0]

        passed_count = total_tests - sum(run_fail_err_skip[1:])
        failed_count = run_fail_err_skip[1]
        errored_count = run_fail_err_skip[2]

        results.results_numbers = passed_count, failed_count, errored_count

        if total_tests == 0:
            return results

        # get specific test results
        xml_blocks = re.findall(r'(<\?xml.*?</testsuite>)', x, re.DOTALL)
        results.xml_blocks = xml_blocks


        passed = []
        failed = []
        errored = []

        for xml_block in xml_blocks[::-1]:
            passed = []
            failed = []
            errored = []

            try:
                root = ET.fromstring(xml_block)

                # Loop over each <testcase> element.
                for testcase in root.findall('testcase'):
                    test_name = testcase.attrib.get('name')
                    # If a <failure> or <error> tag exists as a child, mark accordingly.
                    if testcase.find('failure') is not None:
                        failed.append(test_name)
                    elif testcase.find('error') is not None:
                        errored.append(test_name)
                    else:
                        passed.append(test_name)

            except Exception as e:
                print("Error parsing XML:", e)

            if len(passed) == passed_count and len(failed) == failed_count and len(errored) == errored_count:
                break

        results.results = passed, failed, errored

        return results


    def set_up(self, temp_dir, _, output_path):
        """
        Sets up the environment for execution. Should be called once in the beginning of the Analysis
        :param temp_dir:
        :param output_path:
        :return: The
        """
        print("Mavenbuilder: setup")
        wrapper = DockerizedWrapper()
        dock_context = {
            "image": self.old_image_name,
            "new_image": self.image,
            "directory": temp_dir,
            "command": f"timeout 180 mvn {self.set_up_maven_command} {self.set_up_maven_args}; RET=$?; rm -rf ../root/*; exit $RET;",
        }
        return wrapper.setup_image(dock_context, output_path)


    def tear_down(self, _):
        print("Mavenbuilder: teardown  current image is", self.image)
        wrapper = DockerizedWrapper()
        dock_context = {
            "new_image": self.image,
        }
        wrapper.remove_image(dock_context)

