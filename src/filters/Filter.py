from typing import List
from src.filters.FilterFunction import FilterFunction
from src.filters.NoFilter import NoFilter

class Filter:
    def __init__(self, filter_functions: List[FilterFunction]):
        self.filter_functions = filter_functions
        self.filter_functions.append(NoFilter())

    def filter_all(self, data: List[dict], output_path: str) -> List[dict]:
        # TODO explain this
        filtered_data = filter(lambda x: all([f(x) for f in self.filter_functions]), data)

        return list(filtered_data)

        # TODO add saving filtered list