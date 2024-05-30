import json

import tiktoken

from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from cascade.utils.JavaUtils import build_context

import copy
import os


class GPT35JavaTestGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=2048, temperature=0, delay=3, dummy=False, max_prompt_tokens=2000, debug=False, freq_penalty=0.0):
        super().__init__()
        self.debug = debug
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay, dummy=dummy, freq_penalty=freq_penalty)

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo-instruct")

        setup = f"// SETUP: Write Java JUnit tests for {context['signature']['name']}\n\n// CODE:\n\n"

        code = build_context(context, doc=True) + ";\n}\n\n// TEST:\n\n"

        test_header = self.build_tests(context, primer=f"\n    // write tests for {context['signature']['name']} here\n")

        prompt = setup + code + test_header


        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True)
            prompt = setup + code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True)
            prompt = setup + code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True)
            prompt = setup + code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = build_context(context, doc=True, no_fields=True, no_constructors=True,  no_other_method_docs=True, no_other_methods=True)
            prompt = setup + code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return ""

        return prompt

    def build_tests(self, context, primer=""):
        packg_declaration = f"package {context['test_package']};\n\n"
        imports = "".join(context["test_imports"]) + "\n"
        classdefinition = "public class " + context["test_file_path"].split("/")[-1].split(".")[0] + "{"
        name = str(context["signature"]["name"])
        func_definition = "    @Test\n    public void test" + name[0].upper() + name[1:] + "1(){"
        return packg_declaration + imports + classdefinition + primer + func_definition

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
        if self.debug:
            print(response)



        new_test = response["choices"][0]["text"]

        if response["choices"][0]["finish_reason"] == "length":
            new_test = self.try_to_fix(new_test)


        new_test = self.build_tests(context) + new_test

        return new_test , response

    def try_to_fix(self, new_test):
        last_test = 0
        lines = new_test.splitlines()
        for num, line in enumerate(lines):
            if "@Test" in line:
                last_test = num
        return "\n".join(lines[:last_test]) + "\n}"
