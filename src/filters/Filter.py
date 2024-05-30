import copy
import os.path
from types import MappingProxyType
from typing import List
from src.filters.FilterFunction import FilterFunction
from src.filters.NoFilter import NoFilter
from src.utils.Utils import *

class Filter:
    def __init__(self, filter_functions: List[FilterFunction]):
        self.filter_functions = filter_functions
        self.filter_functions.append(NoFilter())

    def filter_all(self, data: List[dict]) -> List[dict]:
        filtered_data = list(filter(lambda x: all([f(copy.deepcopy(x)) for f in self.filter_functions]), data))

        return filtered_data

