import copy
import json
import os

from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT4Executor import GPT4Executor
from cascade.utils.PythonUtils import build_signature


class GPT4TestGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=1000, temperature=0, delay=3, freq_penalty=0.0, dummy=False):
        super().__init__()
        self.prompt_executor = GPT4Executor(max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature,
                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

    def build_prompt(self, context):
        sig_and_doc = build_signature(context, doc=True)
        prompt = sig_and_doc + "\n    pass"

        unittestprompt = f"\n\n# Tests:\nimport unittest\n\nclass test_{context['signature']['name']}(unittest.TestCase):\n"

        prompt += unittestprompt


        system_prompt =  "Write python unittests for this function."

        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist

    def generate(self, context, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)
        test_safety_copy_path = os.path.join(output_path, safety_copy_prefix + "test_generator_current.json")

        response = None
        if os.path.exists(test_safety_copy_path):
            with open(test_safety_copy_path, "r") as file:
                context2 = json.load(file)

            response = context2["response"]
            del context2["response"]
            context2["root_path"] = context["root_path"]

            if context != context2:
                response = None

        if not response:
            response = self.prompt_executor.execute(prompt).model_dump()

            savety_copy = copy.deepcopy(context)
            savety_copy["response"] = response

            with open(test_safety_copy_path , "w") as file:
                json.dump(savety_copy, file)

        new_test = response["choices"][0]["message"]["content"]

        new_test = "import unittest\nfrom func import *\n\nclass test_func(unittest.TestCase):\n" + new_test

        return new_test , response
