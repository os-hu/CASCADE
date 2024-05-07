from src.filters.FilterFunction import FilterFunction


class NoTestsFilterFunction(FilterFunction):
    def filter(self, context) -> bool:
        return "tests" in context
