import copy

from cascade.analysis.executor.AnalysisExecutor import AnalysisExecutor


class Execution:
    def __init__(self, executor: AnalysisExecutor):
        self.executor = executor

    def execute(self, code, tests, context, output_path):
        return self.executor.execute(code, tests, copy.deepcopy(context), output_path)


    def set_up(self, data, output_path):
        return self.executor.set_up(data, output_path)


    def tear_down(self, data):
        return self.executor.tear_down(data)
