from src.generation.Generator import Generator
from src.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from src.utils.JavaUtils import build_context

import os
import copy
import re
import tiktoken

class GPT35JavaCodeGenerator(Generator):
    def __init__(self, max_attempts=1, max_prompt_tokens=1600, max_tokens=800, temperature=0, delay=3, dummy=False):
        super().__init__()
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay, dummy=dummy)

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo-instruct")


        setup = f"// SETUP: Write Java code for {context['signature']['name']}\n\n"

        packg_declaration = f"package {context['package']};\n\n"

        imports = "".join(context["parent"]["imports"]) + "\n"

        code = build_context(context, doc=True) + "{"

        prompt = setup + packg_declaration + imports + code

        len(enc.encode(prompt))

        return prompt


    def generate(self, context, output_path):
        prompt = self.build_prompt(context)

        response = self.prompt_executor.execute(prompt).model_dump()

        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response

        with open(os.path.join(output_path, "code_generator_current.json") , "w") as file:
            file.write(str(savety_copy))

        # TODO if max tokens have been used  cut the response down?
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
