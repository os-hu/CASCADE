from abc import ABC, abstractmethod

from cascade.Requirements import Requirements
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.visualizer.Visualization import Visualization
from cascade.generation.Generation import Generation

class Analysis(ABC):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization):
        self.generator = generator
        self.executor = executor
        self.visualizer = visualizer
        self.provided = Requirements(Requirements.Kind.PROVIDED, name="Analysis-Provided")
        self.provided.add_requirement("all", Requirements.Level.MANDATORY)
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Analysis-Extraction-Expected")


    @abstractmethod
    def analyse(self, data, output_path):
        """
        This is the main analysis method.
        :return:
        """
        pass
