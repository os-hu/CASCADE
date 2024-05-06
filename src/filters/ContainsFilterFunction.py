import re

from src.filters.FilterFunction import FilterFunction
from src.utils import Utils


class ContainsFilterFunction(FilterFunction):
    def __init__(self, key, content, iterate=True, re=False, invert=False, return_value_if_not_exists=False):
        """
        A filter that is used .

        If the requirements contain 'all', they will NOT be verified

        :param data: The dictionary on which the requirements are supposed to hold

        :raise RequirementsMismatchException: If any :class:`Requirements.Level`.MANDATORY requirements were not fulfilled

        :return: True if all mandatory requirements are fulfilled (e.g., the key exists)
        """

        self.return_value_if_not_exists = return_value_if_not_exists
        self.invert = invert
        self.re = re
        self.iterate = iterate
        self.content = content
        self.key = key

    def filter(self, context) -> bool:
        value = Utils.get_value_from_context(self.key, context, lambda x: None)
        if isinstance(value, list):
            if self.iterate:
                for sub_value in value:
                    if self.check_if_contains(sub_value, self.content):
                        return not self.invert
            else:
                return self.return_value_if_not_exists
        else:
            return self.check_if_contains(value, self.content)

    def check_if_contains(self, value, content):
        if self.re:
            found = bool(re.search(content, value))
        else:
            found = content in value
        if self.invert:
            return not found
        else:
            return found
