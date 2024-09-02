from cascade.analysis.executor.AnalysisExecutor import succeeded, failed, errored
from cascade.analysis.executor.MavenJavaExecutor import MavenJavaExecutor
from cascade.analysis.executor.builders.MavenBuilder import MavenBuilder


class DatasetMavenJavaExecutor(MavenJavaExecutor):
    def __init__(self):
        super().__init__()
        self.args = ["", "-Dskip.rat=true"]

    def execute(self, code: str, tests: str, context: dict, output_path) -> (succeeded, failed, errored):

        # buidl looop

        super().execute(code, tests, context, output_path)

        # if it wokred set args to the working arg