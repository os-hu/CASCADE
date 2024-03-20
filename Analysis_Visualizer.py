from abc import ABC, abstractmethod

class Analysis_Visualizer(ABC):
    @abstractmethod
    def visualize(self, data):
        """
        This is used to vizualize the results of the analysis module
        :param data: the data to be visualized
        """
        pass
