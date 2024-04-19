from src.abstract_classes.Code_Generator import Code_Generator
from src.abstract_classes.Test_Generator import Test_Generator

class Generation:
    """
    TODO
    """
    def __init__(self, code_generator: Code_Generator, test_generator: Test_Generator):
        """
        TODO
        """

        self.code_generator = code_generator
        self.test_generator = test_generator

    def generate_code(self, context):
        """
        TODO
        """
        code = self.code_generator.generate(context)

        return code

    def generate_tests(self, context):
        """
        TODO
        """
        tests = self.test_generator.generate(context)

        return tests
