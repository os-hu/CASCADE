import copy

from cascade.generation.Generator import Generator


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

    def generate_code(self, context, input_path, output_path, safety_copy_prefix=""):
        """
        TODO
        :param input_path:
        """
        context_ = copy.deepcopy(context)
        code, response = self.code_generator.generate(context_, input_path, output_path, safety_copy_prefix)
        del context_
        return code, response

    def generate_tests(self, context, input_path, output_path, safety_copy_prefix=""):
        """
        TODO
        :param input_path:
        """
        context_ = copy.deepcopy(context)
        tests, response = self.test_generator.generate(context_, input_path, output_path, safety_copy_prefix)
        del context_
        return tests, response

    def generate_doc(self, context, input_path, output_path, safety_copy_prefix=""):
        """
        TODO
        :param input_path:
        """
        context_ = copy.deepcopy(context)
        doc, response = self.doc_generator.generate(context_, input_path, output_path, safety_copy_prefix)
        del context_
        return doc, response
