from abc import ABC, abstractmethod
from typing import NewType

succeeded = NewType("succeeded", list[str])
failed = NewType("failed", list[str])
errored = NewType("errored", list[str])

class Analysis_Executor(ABC):
    @abstractmethod
    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):
        """
        This executes the provided tests against the code.
        This should be done in some kind of sandbox as the passed code and tests can not be guaranteed to be safe

        :param code:
        :param tests:
        :param context:

        :return: TODO
        """
        pass
