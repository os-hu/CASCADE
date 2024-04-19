from src.abstract_classes.Code_Generator import Code_Generator
from src.implementations.generation.prompt_executor.GPT35Completion_Prompt_Executor import GPT35Completion_Prompt_Executor

class GPT35_Code_Generator(Code_Generator):
    def __init__(self, api_key_path, max_attempts=1, max_tokens=800, temperature=0, delay=3):
        self.executor = GPT35Completion_Prompt_Executor(api_key_path, max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature, delay=delay)
        self.context = {}

    def build_prompt(self):
        pass

    def generate(self, context):


        pass

