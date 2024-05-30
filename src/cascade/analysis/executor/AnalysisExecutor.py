from abc import ABC, abstractmethod
from typing import NewType

from cascade.Requirements import Requirements

succeeded = NewType("succeeded", list[str])
failed = NewType("failed", list[str])
errored = NewType("errored", list[str])


class AnalysisExecutor(ABC):
    def __init__(self):
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Executor-Extraction-Expected")
        self.analysis_requirements = Requirements(Requirements.Kind.EXPECTED, name="Executor-Analysis-Expected")

    @abstractmethod
    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):
        """
        This executes the provided tests against the code.
        This should be done in some kind of sandbox as the passed code and tests can not be guaranteed to be safe

        :param code:
        :param tests:
        :param context:

        :return: TODO
        """
        pass

    @abstractmethod
    def set_up(self, context):
        pass

    @abstractmethod
    def tear_down(self, context):
        pass