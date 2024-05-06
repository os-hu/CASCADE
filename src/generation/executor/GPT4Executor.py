from openai import OpenAI
import time

from src.generation.executor.PromptExecutor import PromptExecutor


class GPT4Executor(PromptExecutor):
    def __init__(self, api_key_path, max_attempts=1, max_tokens=1200, temperature=0, delay=3):
        # read in api key
        # TODO add other way to add api key than string in a file

        with open(api_key_path, "r") as file:
            api_key = file.read()

        self.client = OpenAI(api_key=api_key)

        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay

    def execute(self, prompt):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )

                return response

            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)  # Wait for delay seconds before retrying

        return {}


