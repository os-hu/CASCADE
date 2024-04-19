from openai import OpenAI
import time
class GPT35Completion_Prompt_Executor():
    def __init__(self, api_key_path, max_attempts=1, max_tokens=800, temperature=0, delay=3):
        # read in api key
        # TODO add other way to add api key than string in a file

        with open(api_key_path, "r") as file:
            api_key = file.read()

        self.client = OpenAI(api_key=api_key)

        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay

    def generate(self, prompt):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                response = self.client.completions.create(
                    model="gpt-3.5-turbo-instruct",
                    prompt=prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )

                return response

            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)  # Wait for delay seconds before retrying

        return {}


