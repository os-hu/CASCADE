import copy
from types import MappingProxyType

from src.analysis.executor.AnalysisExecutor import AnalysisExecutor


class Execution:
    def __init__(self, executor: AnalysisExecutor):
        self.executor = executor

    def execute(self, code, tests, context):
        return self.executor.execute(code, tests, copy.deepcopy(context))
