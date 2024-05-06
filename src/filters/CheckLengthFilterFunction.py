from enum import Enum

from src.filters.FilterFunction import FilterFunction
from src.utils import Utils


class Operators(Enum):
    GREATER = 0
    GREATER_EQUAL = 1
    EQUAL = 2
    UNEQUAL = 3
    SMALLER_EQUAL = 4
    SMALLER = 5


class CheckLengthFilterFunction(FilterFunction):
    def __init__(self, key, op, val):
        """
        A filter that is used to check if a key has a certain length, if the key does not exist or does not support
        :builtin:`len()`, it returns False.

        Keys are evaluated hierarchically, so to check "name" in {"signature": {"name": "test"}}, the key would be
        "signature.name".

        :param key: The dictionary key in question
        :param op: The operator that is used in the comparison from :class:`Operators`
        :param val: The value to compare to
        """
        self.key = key
        self.op = op
        self.val = val

    def filter(self, context) -> bool:
        value = Utils.get_value_from_context(self.key, context, lambda x: None)
        try:
            functions = {
                Operators.GREATER: lambda x, y: x > y,
                Operators.GREATER_EQUAL: lambda x, y: x >= y,
                Operators.EQUAL: lambda x, y: x == y,
                Operators.UNEQUAL: lambda x, y: x != y,
                Operators.SMALLER_EQUAL: lambda x, y: x <= y,
                Operators.SMALLER: lambda x, y: x == y,
            }
            functions[self.op](len(value), self.val)
        except Exception as e:
            print(e)
            return False
