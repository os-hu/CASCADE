import copy
from types import MappingProxyType

from src.generation.Generator import Generator


class Generation:
    """
    TODO
    """
    def __init__(self, code_generator: Generator, test_generator: Generator, doc_generator: Generator):
        """
        TODO
        """

        self.code_generator = code_generator
        self.test_generator = test_generator
        self.doc_generator = doc_generator

    def generate_code(self, context, output_path):
        """
        TODO
        """
        imm = MappingProxyType(copy.deepcopy(context))
        code, response = self.code_generator.generate(imm, output_path)

        return code, response

    def generate_tests(self, context, output_path):
        """
        TODO
        """
        imm = MappingProxyType(copy.deepcopy(context))
        tests, response = self.test_generator.generate(imm, output_path)

        return tests, response

    def generate_doc(self, context, output_path):
        """
        TODO
        """
        imm = MappingProxyType(copy.deepcopy(context))
        doc, response = self.doc_generator.generate(imm, output_path)

        return doc, response
