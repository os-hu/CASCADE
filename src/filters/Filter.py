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

    def filter_all(self, data: List[dict], output_path: str) -> List[dict]:
        # TODO explain this

        file_path = os.path.join(output_path, "filtered.json")

        if os.path.exists(file_path):
            filtered_data = load_json_from_path(file_path)
        else:
            filtered_data = list(filter(lambda x: all([f(MappingProxyType(copy.deepcopy(x))) for f in self.filter_functions]), data))

        save_dicts_list_to_json(filtered_data, file_path)

        return filtered_data

