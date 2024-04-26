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

    def generate_code(self, context, output_path):
        """
        TODO
        """
        code, response = self.code_generator.generate(context, output_path)

        return code, response



    def generate_tests(self, context, output_path):
        """
        TODO
        """
        tests, response = self.test_generator.generate(context, output_path)

        return tests, response
