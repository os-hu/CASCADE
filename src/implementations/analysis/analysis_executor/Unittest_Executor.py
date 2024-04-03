from src.abstract_classes.Analysis_Executor import Analysis_Executor, succeeded, failed, errored


class Unittest_Executor(Analysis_Executor):
    def __init__(self):
        pass

    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):
        return [], [], []
