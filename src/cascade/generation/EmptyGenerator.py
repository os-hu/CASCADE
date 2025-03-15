from cascade.generation.Generator import Generator


class EmptyGenerator(Generator):
    """
    TODO
    """
    def __init__(self):
        super().__init__()

    def generate(self, context, input_path, output_path):
        """
        TODO
        :param input_path:
        """
        return None
