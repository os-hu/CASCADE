import copy
import json
import os
import re

import tiktoken

from cascade.generation.Generator import Generator
from cascade.generation.executor.OpenAIChatCompletionExecutor import OpenAIChatCompletionExecutor
from cascade.utils.JavaUtils import build_context
from cascade.generation.test.GPT4JavaTestGenerator import GPT4JavaTestGenerator

class GPT4oJavaTestGenerator(GPT4JavaTestGenerator):
    def __init__(self, max_attempts=1, max_tokens=1000, temperature=0, delay=3, max_prompt_tokens=2000, model="gpt-4o", freq_penalty=0.0, dummy=False):
        super().__init__()
        self.model = model
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = OpenAIChatCompletionExecutor(max_attempts=max_attempts, model=model, max_tokens=max_tokens, temperature=temperature,
                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

        self.is_three = False


    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model(self.model)

        system_prompt = f"Write Java JUnit tests for the function {context['signature']['name']}. Respond only with the completion of the tests."



        code = "// CODE:\n\n" + build_context(context, doc=True)

        test_header = ";\n}\n\n// TESTS:\n\n" + self.build_tests(context, primer=f"\n    // start writing tests for {context['signature']['name']} here")

        prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True, no_constructors=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True,
                                 no_other_methods=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return []


        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist