from abc import ABC, abstractmethod

class Extraction(ABC):
    @abstractmethod
    def extract(self, input_path, output_path):
        """
        TODO
        """
        pass
