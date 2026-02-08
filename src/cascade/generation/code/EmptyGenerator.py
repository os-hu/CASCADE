from cascade.generation.Generator import Generator


class EmptyGenerator(Generator):
    """
    default generator doing nothing
    """
    def __init__(self):
        super().__init__()

    def generate(self, context, input_path, output_path):
        """
        TODO
        :param input_path:
        """
        return None