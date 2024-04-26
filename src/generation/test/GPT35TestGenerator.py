from src.generation.Generator import Generator
from src.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from src.utils.PythonUtils import build_signature

import copy
import os


class GPT35TestGenerator(Generator):
    def __init__(self, api_key_path, max_attempts=1, max_tokens=800, temperature=0, delay=3):
        self.prompt_executor = GPT35CompletionExecutor(api_key_path, max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature, delay=delay)

    def build_prompt(self, context):
        setup = "# SETUP: Write python unittests for this function.\n"
        sig_and_doc = build_signature(context, doc=True)
        prompt = setup + sig_and_doc + "\n    pass"

        unittestprompt = "\n\n# Tests:\nimport unittest\n\nclass test_Class(unittest.TestCase):\n"

        prompt += unittestprompt

        return prompt
        #return [{"role": "user", "content": prompt}]

    def generate(self, context, output_path):
        prompt = self.build_prompt(context)
        print(prompt)

        response = self.prompt_executor.execute(prompt).model_dump()


        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response
        #save_dicts_list_to_json([savety_copy], os.path.join(output_path, "code_generator_current.json"))

        with open(os.path.join(output_path, "test_generator_current.json") , "w") as file:
            file.write(str(savety_copy))


        new_code = response["choices"][0]["text"]

        return(new_code , response)
