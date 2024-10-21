from cascade.generation.Generator import Generator


class NoGenerator(Generator):
    """
    TODO
    """
    def __init__(self):
        super().__init__()

    def generate(self, context, input_path, output_path, safety_copy_prefix):
        """
        TODO
        :param input_path:
        """
        return None
