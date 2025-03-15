from abc import ABC, abstractmethod

from cascade.Requirements import Requirements


class Generator(ABC):
    """
    The abstract base class for all generators. This class is designed to be inherited by all generators.
    """
    def __init__(self):
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Generator-Extraction-Expected")
        self.analysis_requirements = Requirements(Requirements.Kind.EXPECTED, name="Generator-Analysis-Expected")

    @abstractmethod
    def generate(self, context, input_path, output_path):
        """
        TODO
        :param context:
        :param input_path:
        :param output_path:
        """
        pass
