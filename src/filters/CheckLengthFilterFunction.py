from enum import Enum

from src.filters.FilterFunction import FilterFunction
from src.utils import Utils

class CheckLengthFilterFunction(FilterFunction):
    def __init__(self, key, op, val):
        """
        A filter that is used to check if a key has a certain length, if the key does not exist or does not support
        :builtin:`len()`, it returns False.

        Keys are evaluated hierarchically, so to check "name" in {"signature": {"name": "test"}}, the key would be
        "signature.name".

        :param key: The dictionary key in question
        :param op: The operator that is used in the comparison from [">", ">=", "==", "!=", "<=", "<"]
        :param val: The value to compare to
        """
        super().__init__()
        self.key = key
        self.op = op
        self.val = val

    def filter(self, context) -> bool:
        value = Utils.get_value_from_context(self.key, context, lambda x: None)
        if value:
            try:
                functions = {
                    ">": lambda x, y: x > y,
                    ">=": lambda x, y: x >= y,
                    "==": lambda x, y: x == y,
                    "!=": lambda x, y: x != y,
                    "<=": lambda x, y: x <= y,
                    "<": lambda x, y: x < y,
                }
                return functions[self.op](len(value), self.val)
            except Exception as e:
                print(e)
                return False
        return False