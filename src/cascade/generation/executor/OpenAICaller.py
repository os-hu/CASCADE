import os
import time
from openai import OpenAI
from cascade.generation.executor.LLMCaller import LLMCaller


class OpenAICaller(LLMCaller):
    """
    Chat-completions caller for OpenAI and OpenAI-compatible servers.

    Local servers such as llama.cpp and vLLM should be configured with
    ``base_url`` or one of the supported environment variables below. Tool
    calling is passed through unchanged using the OpenAI chat-completions
    ``tools``/``tool_calls`` protocol.
    """

    def __init__(
        self,
        max_attempts=1,
        max_tokens=16000,
        temperature=0,
        delay=5,
        dummy=False,
        model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        freq_penalty=0.0,
        base_url=None,
        api_key=None,
        timeout=None,
        token_parameter="auto",
    ):
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay
        self.freq_penalty = freq_penalty
        self.model = model
        self.base_url = (
            base_url
            or os.environ.get("CASCADE_OPENAI_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("LLAMA_CPP_BASE_URL")
        )
        self.token_parameter = token_parameter

        if dummy:
            self.client = None
            return

        if timeout is None:
            timeout = os.environ.get("CASCADE_OPENAI_TIMEOUT")
        if timeout is None:
            timeout = 86400.0

        client_kwargs = {
            "timeout": float(timeout),
        }

        if self.base_url is not None:
            client_kwargs["base_url"] = self.base_url
            client_kwargs["api_key"] = (
                api_key
                or os.environ.get("CASCADE_OPENAI_API_KEY")
                or os.environ.get("LLAMA_CPP_API_KEY")
                or os.environ.get("VLLM_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or "dummy"
            )
        else:
            client_kwargs["api_key"] = (
                api_key
                or os.environ.get("CASCADE_OPENAI_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
            )

        self.client = OpenAI(**client_kwargs)

    def _token_parameter(self, fallback=False):
        if self.token_parameter != "auto":
            return self.token_parameter

        if fallback:
            return "max_completion_tokens" if self.base_url else "max_tokens"

        return "max_tokens" if self.base_url else "max_completion_tokens"

    def _request_kwargs(self, prompt, kwargs, fallback=False):
        request_kwargs = {
            "model": self.model,
            "messages": prompt,
        }

        if self.max_tokens not in (None, 0, -1):
            request_kwargs[self._token_parameter(fallback=fallback)] = self.max_tokens

        if self.temperature is not None:
            request_kwargs["temperature"] = self.temperature

        if self.freq_penalty is not None:
            request_kwargs["frequency_penalty"] = self.freq_penalty

        request_kwargs.update(kwargs)
        return request_kwargs

    def execute(self, prompt, **kwargs):
        attempt = 0
        while attempt < self.max_attempts:
            try:
                request_kwargs = self._request_kwargs(prompt, kwargs)
                return self.client.chat.completions.create(**request_kwargs)

            except Exception as e:
                if self.token_parameter == "auto":
                    try:
                        request_kwargs = self._request_kwargs(prompt, kwargs, fallback=True)
                        return self.client.chat.completions.create(**request_kwargs)
                    except Exception:
                        pass

                print(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)

        raise Exception("Generation failed. because of repeated errors.")
