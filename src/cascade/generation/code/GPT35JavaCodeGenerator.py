from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from cascade.utils.JavaUtils import build_context

import os
import copy
import tiktoken

class GPT35JavaCodeGenerator(Generator):
    def __init__(self, max_attempts=1, max_prompt_tokens=2048, max_tokens=2048, temperature=0, delay=3, dummy=False):
        super().__init__()
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay, stop_sequence=None , dummy=dummy)

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo-instruct")


        setup = f"// SETUP: Write the body of one Java function for {context['signature']['name']}\n\n"

        packg_declaration = f"package {context['package']};\n\n"

        imports = "".join(context["parent"]["imports"]) + "\n"

        code = build_context(context, doc=True)

        primer =  "{\n// write the function body here\n"

        prompt = setup + packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True)
            prompt = setup + packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True)
            prompt = setup + packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True)
            prompt = setup + packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True,  no_other_method_docs=True, no_other_methods=True)
            prompt = setup + packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return ""

        return prompt


    def generate(self, context, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)

        if prompt == "":
            return "", None

        response = self.prompt_executor.execute(prompt).model_dump()

        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response

        with open(os.path.join(output_path, safety_copy_prefix + "code_generator_current.json") , "w") as file:
            file.write(str(savety_copy))

        new_code = response["choices"][0]["text"]

        if response["choices"][0]["finish_reason"] == "stop":
            new_code = self.try_to_fix(new_code)

        return new_code , response

    def try_to_fix(self, new_code):
        lines = new_code.splitlines()
        doc_comment = len(lines)
        for num, line in enumerate(lines):
            if "/**" in line:
                doc_comment = num
                break
        new_code = "\n".join(lines[:doc_comment])

        try:
            if doc_comment == len(lines):
                new_code = new_code[:str(new_code).rindex("}")]
            if new_code.rstrip()[-1] != ";":
                new_code = new_code[:str(new_code).rindex("}")]
        except:
            pass
        return "{" + new_code + "}"
