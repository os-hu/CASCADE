from src.filters.FilterFunction import FilterFunction


class NoFilter(FilterFunction):
    def filter(self, context):
        return True
