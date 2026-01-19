import os
import time
from openai import OpenAI

class VLLMCaller(LLMCaller):
    def __init__(
        self,
        max_attempts=1,
        max_tokens=1200,
        temperature=0,
        delay=5,
        dummy=False,
        model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        freq_penalty=0.0,
        base_url="http://127.0.0.1:8000/v1",
        api_key="dummy",
        timeout=60.0,
    ):
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay
        self.freq_penalty = freq_penalty
        self.model = model

        # For vLLM OpenAI-compatible server:
        # - base_url must include /v1
        # - api_key is usually ignored unless you started vLLM with --api-key
        if not dummy:
            self.client = OpenAI(
                base_url=base_url,
                api_key=os.environ.get("VLLM_API_KEY", api_key),
                timeout=timeout,
            )

    def execute(self, prompt, **kwargs):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    # vLLM may or may not support this depending on version;
                    # if you see 400 errors, remove this line.
                    frequency_penalty=self.freq_penalty,
                    **kwargs,
                )
                return response

            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)

        return {}
