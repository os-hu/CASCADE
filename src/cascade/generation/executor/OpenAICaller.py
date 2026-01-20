import os
import time
from openai import OpenAI
from cascade.generation.executor.LLMCaller import LLMCaller


class OpenAICaller(LLMCaller):
    def __init__(
        self,
        max_attempts=1,
        max_tokens=1200,
        temperature=0,
        delay=5,
        dummy=False,
        model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        freq_penalty=0.0,
        base_url=None,          # ← optional
        api_key=None,           # ← optional
        timeout=60.0,
    ):
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay
        self.freq_penalty = freq_penalty
        self.model = model

        if dummy:
            self.client = None
            return

        client_kwargs = {
            "timeout": timeout,
        }

        if base_url is not None:
            # we expect this to be a vLLM OpenAI-compatible server
            client_kwargs["base_url"] = base_url
            client_kwargs["api_key"] = os.environ.get("VLLM_API_KEY", api_key or "dummy")
        else:
            # Normal OpenAI
            client_kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", api_key)

        self.client = OpenAI(**client_kwargs)

    def execute(self, prompt, **kwargs):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    max_completion_tokens=self.max_tokens,   #temporary fix for gpt5
                    #temperature=self.temperature,
                    frequency_penalty=self.freq_penalty,
                    **kwargs,
                )
                return response

            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)

        raise Exception("Generation failed. because of repeated errors.")


