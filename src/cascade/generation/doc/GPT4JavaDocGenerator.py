from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from cascade.utils.PythonUtils import build_signature

import os
import copy


class GPT4JavaDocGenerator(Generator):
    """
        placeholder class for later functionality
    """
    def __init__(self, max_attempts=1, max_tokens=800, temperature=0, delay=3):
        super().__init__()
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay)

    def build_prompt(self, context):
        return ""

    def generate(self, context, input_path, output_path):
        return "" , ""
