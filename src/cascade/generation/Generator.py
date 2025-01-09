from abc import ABC, abstractmethod

from cascade.Requirements import Requirements


class Generator(ABC):
    """
    TODO
    """
    def __init__(self):
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Generator-Extraction-Expected")
        self.analysis_requirements = Requirements(Requirements.Kind.EXPECTED, name="Generator-Analysis-Expected")

    @abstractmethod
    def generate(self, context, input_path, output_path):
        """
        TODO
        :param input_path:
        """
        pass

    def repair(self, context_, input_path, output_path, errors, key):
        pass
