from ollama import Client

from cascade.generation.executor.LLMCaller import LLMCaller


class OllamaCaller(LLMCaller):
    def __init__(self, host='http://localhost:11434', model='deepseek-r1:8b'):
        self.host = host
        self.model = model
        self.client = Client(self.host)
        pass

    def call(self, prompt: str, systemPrompt = """Your task is to generate unit tests. You are given context about a java class or method and
                        you need to write a test for it. You will need to generate new test cases. Do not describe existing tests.
                        Write a test that is not already in the code."""):
        # client = Client(host='http://localhost:11434')
        # client = Client(host='http://gruenau1.informatik.hu-berlin.de:11434')
        response = self.client.generate(model=self.model, prompt=prompt, system=systemPrompt, stream=False)
        return response
