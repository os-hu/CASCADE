from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT4Executor import GPT4Executor
from cascade.utils.JavaUtils import build_context

import os
import copy
import tiktoken
import json

class GPT4JavaCodeGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=1000, temperature=0, delay=3, max_prompt_tokens=2000, freq_penalty=0.0, dummy=False):
        super().__init__()
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = GPT4Executor(max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature,
                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model("gpt-4")

        system_prompt = f"Write the body of one Java function for {context['signature']['name']}."

        packg_declaration = f"package {context['package']};\n\n"

        imports = "".join(context["parent"]["imports"]) + "\n"

        code = build_context(context, doc=True)

        primer =  "{\n// write the function body here\n"

        prompt = packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True)
            prompt = packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True)
            prompt = packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True)
            prompt = packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True,  no_other_method_docs=True, no_other_methods=True)
            prompt = packg_declaration + imports + code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return ""


        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist


    def generate(self, context, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)
        code_safety_copy_path = os.path.join(output_path, safety_copy_prefix + "code_generator_current.json")


        if prompt == "":
            return "", None

        response = None
        if os.path.exists(code_safety_copy_path):
            with open(code_safety_copy_path, "r") as file:
                context2 = json.load(file)

            response = context2["response"]
            del context2["response"]

            if context != context2:
                response = None

        if not response:
            response = self.prompt_executor.execute(prompt).model_dump()

            safety_copy = copy.deepcopy(context)
            safety_copy["response"] = response

            with open(code_safety_copy_path, "w") as file:
                json.dump(safety_copy, file)

        new_code = response["choices"][0]["message"]["content"]

        if response["choices"][0]["finish_reason"] == "stop":
            new_code = self.try_to_fix(new_code)

        # else:  will likely break later down the pipe anyway

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