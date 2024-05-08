from abc import ABC, abstractmethod

from src.Requirements import Requirements
from src.generation.Generation import Generation
from src.analysis.executor.AnalysisExecutor import AnalysisExecutor
from src.analysis.visualizer.AnalysisVisualizer import AnalysisVisualizer


class Analysis(ABC):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: AnalysisExecutor, visualizer: AnalysisVisualizer):
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
