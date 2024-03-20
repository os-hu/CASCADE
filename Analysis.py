from abc import ABC, abstractmethod
from Analysis_Executor import Analysis_Executor
from Analysis_Visualizer import Analysis_Visualizer


class Analysis(ABC):
    """
    TODO
    """
    def __init__(self, executor: Analysis_Executor, visualizer: Analysis_Visualizer):
        self.executor = executor
        self.visualizer = visualizer

    @abstractmethod
    def analyse(self, *args, **kwargs):
        """
        This is the main analysis method.
        :return:
        """
        pass
