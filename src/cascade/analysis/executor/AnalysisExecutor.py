from abc import ABC, abstractmethod
from typing import NewType

from cascade.Requirements import Requirements

class AnalysisExecutor(ABC):
    def __init__(self):
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Executor-Extraction-Expected")
        self.analysis_requirements = Requirements(Requirements.Kind.EXPECTED, name="Executor-Analysis-Expected")

    @abstractmethod
    def execute(self, code: str, tests: str, context: dict, input_path, output_path: str):
        """
        This executes the specified tests against the code.
        This should be executed in some kind of sandbox as the passed code and tests can not be guaranteed to be safe.

        :param input_path: 
        :param output_path:
        :param code:
        :param tests:
        :param context:

        :return: TODO
        """
        pass

    @abstractmethod
    def set_up(self, data, input_path, output_path):
        pass

    @abstractmethod
    def tear_down(self, context):
        pass