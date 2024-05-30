from cascade.Requirements import Requirements
from cascade.filters.FilterFunction import FilterFunction


class NoTestsFilterFunction(FilterFunction):
    def __init__(self):
        super().__init__()
        self.extraction_requirements.add_requirement("tests", Requirements.Level.MANDATORY)
        self.provided.clear()
        self.provided.add_requirement("tests", Requirements.Level.MANDATORY)

    def filter(self, context) -> bool:
        return "tests" in context
