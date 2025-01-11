import ast
import copy
import json
import os
import re
import subprocess
from platform import system

import tiktoken

from cascade.generation.test.GPT4JavaTestGenerator import GPT4JavaTestGenerator
from cascade.generation.executor.OpenAIChatCompletionExecutor import OpenAIChatCompletionExecutor
from cascade.utils.JavaUtils import build_context, check_syntax, repair_helper_functions, get_repair_helper_functions, build_signature


class MultiStepJavaTestGenerator(GPT4JavaTestGenerator):
    def __init__(self, max_attempts=1, max_tokens=16000, temperature=0, delay=3, max_prompt_tokens=5000, model="gpt-4o-mini-2024-07-18", freq_penalty=0.0, dummy=False, ask_for_imports=False, import_prompt_finisher="Reply with the missing imports, leave out those you don't know the correct package of."):
        super().__init__()
        self.ask_for_imports = ask_for_imports
        self.model = model
        self.import_prompt_finisher = import_prompt_finisher
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = OpenAIChatCompletionExecutor(max_attempts=max_attempts, model=model, max_tokens=max_tokens, temperature=temperature,
                                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

        self.is_three = False


    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model(self.model)

        testframework = ""
        if "junit_version" in context:
            version = context["junit_version"]
            testframework = " Use JUnit version " + (version if version[0].isdigit() else "5") + "."

        par = context['signature']['params']
        params = ", ".join(par) if len(par) > 1 else (par[0] if par else "")

        # system_prompt = f"Write Java tests for the function {context['signature']['name']}. Follow its documentation as closely as possible."

        # The method is not implemented yet so you will be using only its documentation as the ground truth of the expected behavior.
        # Focus on creating tests that cover edge cases, boundary conditions, and all documented behaviors, including thrown exceptions

        system_prompt = f"You are an expert Java developer. You will generate unit tests for a specific method in a provided class.{testframework} You can import anything from the project, but no third party libraries. Handle exceptions properly, and ensure method signatures and calls are correct. The code should compile without errors. The method is not implemented yet so you will be using only its documentation as the ground truth of the expected behavior."

        # This is for test driven development so the tests should be designed to fail if the later implementation does not exactly conform to the documentation.
        c1 = f"The function under test is `{context['signature']['name']}({params})`\n\n Focus on testing: {context["tested_property"]["property"]}. Especially on the following Things: {'\n'.join(context["tested_property"]["tests"])}\nHere is the class containing the function:\n\n```java\n"
        c2 = "; // this is the function to be tested\n\n}\n```\n"
        code = c1 + build_context(context, doc=True) + c2

        # test_header = "\n\n// TESTS:\n\n" + self.build_tests(context, primer=f"\n    // write tests for {context['signature']['name']} here. Take the Documentation as literal as possible.\n")

        test_header = f"\nNow write tests regarding: {context['tested_property']['property']} for the function `{context['signature']['name']}({params})` using the test class skeleton below. Everything that you use has to be added to the imports. Every object you use has to be properly instantiated. Handle any checked exceptions (use try-catch or throws), do not forget type parameters. Match method signatures exactly when overriding or implementing methods. Adhere to the documentation as close as possible when writing the tests and only test for the following things: \n{'\n'.join(context["tested_property"]["tests"])} \nAs a reminder, the documentation for the function is:\n\n```java\n{context['doc']}\n```\n\n Test class:\n"
        test_header = test_header + "\n```java\n" + self.build_tests(context, primer=f"\n    // write {context['tested_property']['property']} tests for {context['signature']['name']} here." + "\n```")

        # add something like?  :    Include necessary constructors if extending a class that requires them.

        prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True,
                                      no_other_method_docs=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True,
                                      no_other_method_docs=True,
                                      no_other_methods=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return []

        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist


    def generate(self, context, input_path, output_path):
        # first given the method documentation and signature, we want to extract possible testcases or properties.
        print("generation Phase 1")
        chat_history = []

        prompt_stage1 = [
        {"role": "system", "content": "You are an Expert Java Developer and Requirements Engineer. You will be given a method signature and its documentation. Your task is to extract testable properties from the documentation."},
        {"role": "user", "content": f"Give me properties that should be tested for the method:\n ```java\n{build_signature(context, doc=True)}\n```\nMake sure the entire functionality exactly as described in the documentation is considered and covered with these tests."}
        ]

        chat_history.append(prompt_stage1)
        response_stage1 = self.prompt_executor.execute(prompt_stage1).model_dump()
        chat_history.append(response_stage1)

        # some type of check if it is ok???
        prompt_stage1.append(response_stage1["choices"][0]["message"])

        # next we aim to convert this list into a usable format and extract the to tested properties


        prompt_stage1.append({"role": "user", "content": f"Now turn this into a JSON array. Where each entry has \"property\" (the tested property) and \"tests\" a list of up to 5 things that should be tested to verify the property" })

        chat_history.append(prompt_stage1)
        response_stage1_part2 = self.prompt_executor.execute(prompt_stage1).model_dump()
        chat_history.append(response_stage1_part2)

        answer_text = response_stage1_part2["choices"][0]["message"]["content"]

        json_blocks = re.findall(r"```json(.*?)\n\s*```", answer_text, flags=re.DOTALL)

        if json_blocks:
            try:
                prop_list = ast.literal_eval(json_blocks[0].strip())
            except Exception as e:
                print("Failure: Could not parse json list because: ", e)
        else:
            print("error extracting test list block")
            return # TODO some error handling

        print(f"    Got {len(prop_list)} potential test properties: {[prop['property'] for prop in prop_list]}")
        print("generation Phase 2")

        final_response = []
        final_new_tests = []

        for prop in prop_list[0:3]:    # make this more.  not just 0:3
            # now generate a test class for each property
            context["tested_property"] = prop

            print("    generate tests for:", prop["property"])
            prompt = self.build_prompt(context)
            chat_history.append(prompt)
            response = self.prompt_executor.execute(prompt).model_dump()
            chat_history.append(response)

            new_test = self.extract_tests(response["choices"][0]["message"]["content"], context, response, output_path)

            prompt.append({"role": "assistant", "content": f"´´´java\n{new_test}\n```"})

            calls = re.findall(r"new (.*?)\(", new_test, flags=re.DOTALL)
            if calls:
                tree = subprocess.check_output(["tree", "-P", "*.java", "--charset=ascii", input_path]).decode("utf-8")
                repair_question = f"{', '.join(calls)} {'are' if len(calls) > 1 else 'is'} 'new', check if there are missing imports and fix them using this directory structure:\n```\n{tree}\n```"
                prompt.append({"role": "user", "content": repair_question})

                chat_history.append(prompt)
                repair_response = self.prompt_executor.execute(prompt).model_dump()
                chat_history.append(repair_response)

                new_test = self.extract_tests(repair_response["choices"][0]["message"]["content"], context, repair_response, output_path)

            final_response.append({"property" : prop["property"], "chat_history" : chat_history} )
            final_new_tests.append({ "test_class" : new_test , "property" : prop["property"]})

        # remove the tested property entry from the context dict
        del context["tested_property"]
        return final_new_tests, final_response
