from abc import ABC, abstractmethod


class Builder(ABC):
    def __init__(self, test_pattern="", eval_function=None, image=""):
        self.test_pattern = test_pattern
        self.eval_function = eval_function
        self.image = image

    @abstractmethod
    def build(self, temp_dir):
        pass
