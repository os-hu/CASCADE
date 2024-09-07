from cascade.analysis.executor.AnalysisExecutor import succeeded, failed, errored
from cascade.analysis.executor.MavenJavaExecutor import MavenJavaExecutor
from cascade.analysis.executor.builders.MavenBuilder import MavenBuilder


class DatasetMavenJavaExecutor(MavenJavaExecutor):
    def __init__(self):
        super().__init__()
        # this can be changed to include more arguments that might be used for executing maven
        self.args = ["", "-Dskip.rat=true", "-DforkMode=never"]

    def execute(self, code: str, tests: str, context: dict, input_path, output_path) -> (succeeded, failed, errored):

        # TODO? get mven to display all possbile paramters that migth be used here

        for arg in self.args:
            # try to run maven with the arg
            print("Trying arg: ", arg)
            self.builder = MavenBuilder(
                new_image_name="maven", # should be maven_modified but we dont do a setup here so this is a workaround
                maven_args=arg,
                set_up_maven_command="test",
                set_up_maven_args=arg,
                image="maven",
                timeout=240
            )

            result = super().execute(code, tests, context, input_path, output_path)

            if not result == ([],[],[]):
                # if it worked set args to the working arg
                self.args = [arg]
                print("Working arg: ", arg)
                return result

        return [],[],[]
