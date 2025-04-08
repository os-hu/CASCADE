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

        def describe_structure(data, path="root"):
            if isinstance(data, dict):
                for key, value in data.items():
                    new_path = f"{path}.{key}"
                    print(f"{new_path}: {type(value).__name__}")
                    describe_structure(value, new_path)
            elif isinstance(data, list):
                print(f"{path}: list (length {len(data)})")
                for i, item in enumerate(data[:3]):  # Show structure of first few elements
                    describe_structure(item, f"{path}[{i}]")
                if len(data) > 3:
                    print(f"{path}[...]: (truncated)")
            else:
                # base case: simple value
                print(f"{path}: {type(data).__name__}")

        print("----------------------")
        describe_structure(response)
        return response.model_dump()