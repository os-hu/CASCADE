from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from cascade.utils.PythonUtils import build_signature

import os
import copy
import re

class GPT35CodeGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=800, temperature=0, delay=3, dummy=False):
        super().__init__()
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay, dummy=dummy)

    def build_prompt(self, context):
        setup = "# SETUP: Write functional correct python code.\n\n"
        sig_and_doc = build_signature(context, doc=True)
        prompt = setup + sig_and_doc

        return prompt

    def generate(self, context, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)

        response = self.prompt_executor.execute(prompt).model_dump()

        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response

        with open(os.path.join(output_path, safety_copy_prefix + "code_generator_current.json") , "w") as file:
            file.write(str(savety_copy))

        new_code = response["choices"][0]["text"]
        indent = re.match(r"\s*" , new_code)[0]
        indent = indent.replace("\n" , "")
        indent_length = len(indent)

        temp_new_code = []
        for line in new_code.splitlines():
            if line.startswith(indent):
                line = line[indent_length:]
            temp_new_code.append(line)

        new_code = "\n".join(temp_new_code)

        return new_code , response
