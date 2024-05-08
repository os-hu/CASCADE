from abc import ABC, abstractmethod

from src.Requirements import Requirements


class AnalysisVisualizer(ABC):
    def __init__(self):
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Visualizer-Extraction-Expected")
        self.analysis_requirements = Requirements(Requirements.Kind.EXPECTED, name="Visualizer-Analysis-Expected")

    @abstractmethod
    def visualize(self, data, **kwargs):
        """
        This is used to visualize the results of the analysis module
        :param data: the data to be visualized
        """
        pass
