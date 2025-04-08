import os

from openai import OpenAI
import time

from cascade.generation.executor.LLMCaller import LLMCaller


class OpenAICaller(LLMCaller):
    def __init__(self, max_attempts=1, max_tokens=1200, temperature=0, delay=5, dummy=False, model="gpt-4o-mini", freq_penalty=0.0):
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay
        self.freq_penalty = freq_penalty
        self.model = model
        # read in api key
        if not dummy:
            if "OPENAI_API_KEY" in os.environ:
                api_key = os.environ["OPENAI_API_KEY"]
            else:
                raise Exception("No api key in environment")
            self.client = OpenAI(api_key=api_key)


    def execute(self, prompt, **kwargs):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    frequency_penalty=self.freq_penalty,
                    **kwargs
                )
                return response

            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)  # Wait for delay seconds before retrying

        return {}


