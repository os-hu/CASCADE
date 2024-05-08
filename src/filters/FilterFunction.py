from abc import ABC, abstractmethod

from src.Requirements import Requirements


# beim init get loaded filterfuncs

 # TODO filter all filters func      für alle entries i ndata   also für jeden einzelenne context check if all filters say true  otherweise remove form data


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
