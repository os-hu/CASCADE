import copy

from cascade.analysis.executor.AnalysisExecutor import AnalysisExecutor


class Execution:
    def __init__(self, executor: AnalysisExecutor):
        self.executor = executor

    def execute(self, code, tests, context):
        return self.executor.execute(code, tests, copy.deepcopy(context))


    def set_up(self, data):
        return self.executor.set_up(data)


    def tear_down(self, data):
        return self.executor.tear_down(data)
