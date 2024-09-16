import copy
from typing import List

from cascade.filters.FilterFunction import FilterFunction
from cascade.filters.NoFilter import NoFilter


class Filter:
    def __init__(self, filter_functions: List[FilterFunction]):
        self.filter_functions = filter_functions
        self.filter_functions.append(NoFilter())

    def filter_all(self, data: List[dict]) -> List[dict]:
        filtered_data = [x for x in data if all([f(copy.deepcopy(x)) for f in self.filter_functions])]

        return filtered_data

