from abc import ABC, abstractmethod


class AnalysisVisualizer(ABC):
    @abstractmethod
    def visualize(self, data):
        """
        This is used to visualize the results of the analysis module
        :param data: the data to be visualized
        """
        pass
