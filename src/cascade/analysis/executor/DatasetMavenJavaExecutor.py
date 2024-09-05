from cascade.analysis.executor.AnalysisExecutor import succeeded, failed, errored
from cascade.analysis.executor.MavenJavaExecutor import MavenJavaExecutor
from cascade.analysis.executor.builders.MavenBuilder import MavenBuilder


class DatasetMavenJavaExecutor(MavenJavaExecutor):
    def __init__(self):
        super().__init__()
        # this can be changed to include more arguments that might be used for executing maven
        self.args = ["", "-Dskip.rat=true"]

    def execute(self, code: str, tests: str, context: dict, output_path) -> (succeeded, failed, errored):

        # TODO? get mven to display all possbile paramters that migth be used here

        for arg in self.args:
            # try to run maven with the arg
            print("Trying arg: ", arg)
            self.builder = MavenBuilder(
                new_image_name="maven_modified",
                maven_args=arg,
                set_up_maven_command="test",
                set_up_maven_args=arg,
                image="maven"
            )

            result = super().execute(code, tests, context, output_path)

            if not result == ([],[],[]):
                # if it worked set args to the working arg
                self.args = [arg]
                print("Working arg: ", arg)
                return result

        return [],[],[]
