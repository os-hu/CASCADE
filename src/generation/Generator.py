from abc import ABC, abstractmethod


class Generator(ABC):
    """
    TODO
    """

    @abstractmethod
    def generate(self, context, output_path):
        """
        TODO
        """
        pass
