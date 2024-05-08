import copy
from types import MappingProxyType

from AnalysisExecutor import AnalysisExecutor


class Execution:
    def __init__(self, executor: AnalysisExecutor):
        self.executor = executor

    def execute(self, code, tests, context):
        imm = MappingProxyType(copy.deepcopy(context))
        self.executor.execute(code, tests, imm)
