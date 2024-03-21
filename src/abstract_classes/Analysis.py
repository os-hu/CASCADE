from abc import ABC, abstractmethod

from src.Generation import Generation
from Analysis_Executor import Analysis_Executor
from Analysis_Visualizer import Analysis_Visualizer


class Analysis(ABC):
    """
    TODO
    """
    def __init__(self,  generator: Generation, executor: Analysis_Executor, visualizer: Analysis_Visualizer):
        self.generator = generator
        self.executor = executor
        self.visualizer = visualizer


    @abstractmethod
    def analyse(self, *args, **kwargs):
        """
        This is the main analysis method.
        :return:
        """
        pass
