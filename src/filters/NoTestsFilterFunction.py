from src.filters.FilterFunction import FilterFunction


class ContainsFilterFunction(FilterFunction):
    def filter(self, context) -> bool:
        return "tests" in context
