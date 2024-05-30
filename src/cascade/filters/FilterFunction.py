from abc import ABC, abstractmethod

from cascade.Requirements import Requirements

class FilterFunction(ABC):
    def __init__(self):
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="FilterFunction-Extraction-Expected")
        self.provided = Requirements(Requirements.Kind.PROVIDED, name="FilterFunction-Provided")
        self.provided.add_requirement("all", Requirements.Level.MANDATORY)

    def __call__(self, *args, **kwargs):
        return self.filter(*args)

    @abstractmethod
    def filter(self, context) -> bool:
        pass
