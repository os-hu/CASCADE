from abc import ABC, abstractmethod

class PromptExecutor(ABC):

    @abstractmethod
    def execute(self, prompt):
        pass