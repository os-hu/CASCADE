from ollama import Client

from cascade.generation.executor.LLMCaller import LLMCaller


class OllamaCaller(LLMCaller):
    def __init__(self, host, model):
        self.host = host
        self.model = model
        self.client = Client(self.host)


    def execute(self, prompt, **kwargs):
        response = self.client.chat(model=self.model, messages=prompt, stream=False)
        print(response)

        return dict(response)