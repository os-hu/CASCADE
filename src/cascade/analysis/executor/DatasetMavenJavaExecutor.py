import uuid

from cascade.analysis.executor.AnalysisExecutor import succeeded, failed, errored
from cascade.analysis.executor.MavenJavaExecutor import MavenJavaExecutor
from cascade.analysis.executor.builders.MavenBuilder import MavenBuilder
from cascade.utils.DockerizedWrapper import DockerizedWrapper


class DatasetMavenJavaExecutor(MavenJavaExecutor):
    def __init__(self):
        super().__init__()
        self.initialized = False

        # this can be changed to include more arguments that might be used for executing maven
        self.id = str(uuid.uuid4())
        self.args = ["-fae -Drat.skip=true -DforkMode=never -Dsurefire.failIfNoSpecifiedTests=false"]#["-fae -Dsurefire.failIfNoSpecifiedTests=false", "-fae -Drat.skip=true -Dsurefire.failIfNoSpecifiedTests=false", "-fae -Drat.skip=true -DforkMode=never -Dsurefire.failIfNoSpecifiedTests=false"]

    def execute(self, code: str, tests: str, context: dict, input_path, output_path) -> (succeeded, failed, errored):
        if not self.initialized:
            self.initialized = True
            docker_context = {
                "image": "maven",
                "new_image": "dataset-" + self.id,
                "command": ""
            }
            DockerizedWrapper().setup_image(docker_context,output_path)

        for arg in self.args:
            # try to run maven with the arg
            #print("Trying arg: ", arg)
            self.builder = MavenBuilder(
                new_image_name="dataset-" + self.id,
                maven_args=arg,
                set_up_maven_command="test",
                set_up_maven_args=arg,
                image="maven",
                timeout=180
            )

            result = super().execute(code, tests, context, input_path, output_path)

            if not result[0] == ([],[],[]):
                # if it worked set args to the working arg
                self.args = [arg]
                break
                #print("Working arg: ", arg)

        return result
