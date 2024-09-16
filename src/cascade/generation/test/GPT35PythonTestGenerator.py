from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from cascade.utils.PythonUtils import build_signature

import copy
import os


class GPT35TestGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=1000, temperature=0, delay=3, freq_penalty=0.0, dummy=False):
        super().__init__()
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay, freq_penalty=freq_penalty, dummy=dummy)

    def build_prompt(self, context):
        setup = "# SETUP: Write python unittests for this function.\n"
        sig_and_doc = build_signature(context, doc=True)
        prompt = setup + sig_and_doc + "\n    pass"

        unittestprompt = f"\n\n# Tests:\nimport unittest\n\nclass test_{context['signature']['name']}(unittest.TestCase):\n"

        prompt += unittestprompt

        return prompt
        #return [{"role": "user", "content": prompt}]

    def generate(self, context, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)

        response = self.prompt_executor.execute(prompt).model_dump()


        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response
        #save_dicts_list_to_json([savety_copy], os.path.join(output_path, "code_generator_current.json"))

        with open(os.path.join(output_path, safety_copy_prefix + "test_generator_current.json") , "w") as file:
            file.write(str(savety_copy))

        new_test = response["choices"][0]["text"]

        new_test = "import unittest\nfrom func import *\n\nclass test_func(unittest.TestCase):\n" + new_test

        return new_test , response
