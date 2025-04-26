from abc import ABC, abstractmethod

from cascade.Requirements import Requirements
from cascade.analysis.executor.Execution import Execution
from cascade.generation.Generation import Generation

class Analysis(ABC):
    """
    The abstract base class for all analysis classes.
    """
    def __init__(self, generator: Generation, executor: Execution):
        self.generator = generator
        self.executor = executor
        self.provided = Requirements(Requirements.Kind.PROVIDED, name="Analysis-Provided")
        self.provided.add_requirement("all", Requirements.Level.MANDATORY)
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Analysis-Extraction-Expected")


    @abstractmethod
    def analyze(self, data, input_path, output_path):
        """
        TODO
        :param data:
        :param input_path:
        :param output_path:
        """
        pass
