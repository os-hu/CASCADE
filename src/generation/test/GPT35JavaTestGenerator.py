from src.generation.Generator import Generator
from src.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from src.utils.JavaUtils import build_signature

import copy
import os


class GPT35JavaTestGenerator(Generator):
    def __init__(self, api_key_path, max_attempts=1, max_tokens=1000, temperature=0, delay=3, dummy=False):
        self.prompt_executor = GPT35CompletionExecutor(api_key_path, max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature, delay=delay, dummy=dummy)

    def build_prompt(self, context):


        setup = f"// SETUP: Write Java JUnit tests for {context['signature']['name']}\n\n// CODE:\n\n"

        code = build_signature(context, doc=True) + ";\n}\n\n// TEST:\n\n"

        packg_declaration = f"package {context['test_package']};\n\n"

        imports = "".join(context["test_imports"]) + "\n"

        classdefinition = "public class " + context["test_file_path"].split("/")[-1].split(".")[0] + "{"

        prompt = setup + code + packg_declaration + imports + classdefinition

        return prompt

    def generate(self, context, output_path):
        prompt = self.build_prompt(context)

        response = self.prompt_executor.execute(prompt).model_dump()


        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response
        #save_dicts_list_to_json([savety_copy], os.path.join(output_path, "code_generator_current.json"))

        with open(os.path.join(output_path, "test_generator_current.json") , "w") as file:
            file.write(str(savety_copy))


        new_test = response["choices"][0]["text"]

        new_test = "import unittest\nfrom func import *\n\nclass test_func(unittest.TestCase):\n" + new_test

        return new_test , response
