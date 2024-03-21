import Code_Generator, Test_Generator

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

    def generate_code(self, basic_prompt):
        """
        TODO
        """
        code = self.code_generator.generate(basic_prompt)

        return code

    def generate_tests(self, basic_prompt):
        """
        TODO
        """
        tests = self.test_generator.generate(basic_prompt)

        return tests
