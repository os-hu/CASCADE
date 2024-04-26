from abc import ABC, abstractmethod

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


    @abstractmethod
    def analyse(self, data, output_path):
        """
        This is the main analysis method.
        :return:
        """
        pass
