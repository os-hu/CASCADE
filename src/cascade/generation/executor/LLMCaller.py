from abc import ABC, abstractmethod

class LLMCaller(ABC):
    """
        Abstract base class for prompt executors.
    """
    @abstractmethod
    def execute(self, prompt):
        pass