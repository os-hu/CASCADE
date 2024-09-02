from abc import ABC, abstractmethod


class Builder(ABC):
    def __init__(self, test_pattern="", eval_function=None, image=""):
        self.test_pattern = test_pattern
        self.eval_function = eval_function
        self.image = image

    def set_up(self, temp_dir, context, output_path):
        return True

    @abstractmethod
    def tear_down(self, context):
        pass