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
from cascade.utils.JavaUtils import build_context, check_syntax, repair_helper_functions, get_repair_helper_functions, \
    build_signature


class JavaTestGenerator(GPT4JavaTestGenerator):
    def __init__(self, max_attempts=1, max_tokens=16000, temperature=0, delay=3, max_prompt_tokens=10000,
                 model="gpt-4o-mini-2024-07-18", freq_penalty=0.0, dummy=False, ask_for_imports=False,
                 import_prompt_finisher="Reply with the missing imports, leave out those you don't know the correct package of."):
        super().__init__()
        self.ask_for_imports = ask_for_imports
        self.model = model
        self.import_prompt_finisher = import_prompt_finisher
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = OpenAIChatCompletionExecutor(max_attempts=max_attempts, model=model,
                                                            max_tokens=max_tokens, temperature=temperature,
                                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

        self.is_three = False

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model(self.model)

        testframework = ""
        if "junit_version" in context:
            version = context["junit_version"]
            test_framework_instruction = " Use JUnit version " + (version if version[0].isdigit() else "5") + "."

        par = context['signature']['params']
        params = ", ".join(par) if len(par) > 1 else (par[0] if par else "")

        system_prompt = (
            f"You are an expert Java developer. You will generate unit tests for a specific method in a provided class.{test_framework_instruction} "
            "You can import anything from the project itself, but no third party libraries. Handle exceptions properly, and ensure method signatures and calls are correct. "
            "The code should compile without errors. The method is not implemented yet so you will be using only its documentation as the ground truth of the expected behavior. "
            )

        #
        c1 = (
            f"The function under test is `{context['signature']['name']}({params})`\n\n everything else will be tested later. " 
            "Fill out the tests in the test class below. " 
            "This is for test driven development so the tests should be designed to fail if the later implementation does not exactly conform to the documentation.\n\n"
            "In case you need any of the other methods or fields of the class, here is the entire class containing the function under test:\n\n```java\n"
            )
        c2 = "; // this is the function to be tested\n\n}\n```\n"
        prompt_header = c1 + build_context(context, doc=True) + c2

        # test_header = "\n\n// TESTS:\n\n" + self.build_tests(context, primer=f"\n    // write tests for {context['signature']['name']} here. Take the Documentation as literal as possible.\n")

        test_header = (
            f"\nNow write unit tests for the following function using the test class skeleton below.\nFunction:\n```Java{build_signature(context, doc=True)}```\n"
            "import all necessary classes from the project. Every object you use has to be properly instantiated. "
            "Handle any checked exceptions using try-catch or throws, do not forget type parameters. Match method signatures exactly when overriding or implementing methods. "
            f"Adhere to the documentation as close as possible when writing the tests and only fill the tests that are already given.\n"
            f"\nTest class:"
            )
        # TODO mark additional test somehow, instead of saying 'only write'?

        test_header = test_header + "\n```java\n" + self.build_tests(context) + "\n```"

        # add something like?  :    Include necessary constructors if extending a class that requires them.

        prompt = prompt_header + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            prompt_header = c1 + build_context(context, doc=True, no_fields=True) + c2
            prompt = prompt_header + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            prompt_header = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True) + c2
            prompt = prompt_header + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            prompt_header = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True) + c2
            prompt = prompt_header + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            prompt_header = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True, no_other_methods=True) + c2
            prompt = prompt_header + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return []

        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist

    def generate(self, context, input_path, output_path, response_step2=None):
        # first given the method documentation and signature, we want to extract possible testcases or properties.
        print("generation Phase 1")
        chat_history = []

        prompt_step1 = [
            {"role": "system",
             "content": "You are an expert Java developer and requirements engineer. You will be given a method signature and its documentation. Your task is to extract behavior specifications from the documentation that can later be turned into unit tests to ensure the code is a bug free and faithful to its documentation."},
            {"role": "user",
             "content": f"Give a complete description of the behavior that we should test when assuring code correctness for the following Java method, in particular testable statements of the 'if this then that' type.\n\nThe documentation of the function under test:\n```java\n{build_signature(context, doc=True)}\n```\n\nMake sure you consider the entire functionality exactly as described in the documentation, and all edge cases."}
        ]
        chat_history.append(prompt_step1)
        response = self.prompt_executor.execute(prompt_step1).model_dump()
        chat_history.append(response)

        # some type of check if it is ok???
        prompt_step1.append(response["choices"][0]["message"])
        #print(response_stage1["choices"][0]["message"]["content"])

        # now we aim to convert this text into a usable format and extract the testable properties
        json_listprompt = {"role": "user", "content": f"Now turn this into a JSON array of unit tests we should write for test driven development based on the documentation above. Where each entry has \"test_name\": a name starting with 'test' referencing the specified behavior and \"test_description\": a detailed description for the developer of what this tests should do and which specific behavior from the documentation it tests. Include only those tests that follow directly from the documentation, not performance based ones."}

        #json_listprompt = {"role": "user", "content": f"Now turn this into a JSON array" }

        # possible alterations   to later filter out unnessceary tests
        # To ensure the correctness of the `uniqueIterable` method, we can derive several testable behavior specifications based on the provided documentation. Here are the key behaviors to test, structured in an "if this then that" format:
        # classes:
        #  - "directly from documentation"
        #  - "weitere tests die ausserdem sinnvol sind"
        #  - "performance and integration"
        #  - "compile time tests (e.g. for return types)"

        prompt_step1.append(json_listprompt)
        response = self.prompt_executor.execute(prompt_step1).model_dump()
        chat_history.append(response)

        #print(response_stage1_part2["choices"][0]["message"]["content"])

        # extract json list from response
        answer_text = response["choices"][0]["message"]["content"]
        json_blocks = re.findall(r"```json(.*?)\n\s*```", answer_text, flags=re.DOTALL)
        if json_blocks:
            try:
                # todo json loader
                test_list = json.loads(json_blocks[0].strip())
            except Exception as e:
                print("Failure: Could not parse json list because: ", e)

                # TODO maybe ask llm again?  or some other ways of fixing bad json stuff
                with open("results.txt", "w") as f:
                    f.write("Negative, JSON error")
                with open("errors.txt", "w") as f:
                    f.write("not parsable json answer because: " + str(e))
                    f.write(answer_text)
                return [], []
        else:
            print("error extracting test list block")
            return  # TODO some error handling

        # make sure that all tests begin with test (e.g. instead of ending) and nadding numbers to test cases that have the name
        seen = {}
        for t in test_list:
            base = t["test_name"].replace("test", "").replace("Test", "").strip()
            seen[base] = seen.get(base, 0) + 1
            t["test_name"] = f"test{base}" if seen[base] == 1 else f"test{base}{seen[base]}"


        print(f"    Got {len(test_list)} potential tests: {[test['test_name'] for test in test_list]}")
        print("generation Phase 2")

        # now we have a list of testable properties, we want to generate a testclase with them all.

        context["test_list"] = test_list

        prompt_step2 = self.build_prompt(context)

        chat_history.append(prompt_step2)
        response = self.prompt_executor.execute(prompt_step2).model_dump()

        chat_history.append(response)

        prompt_step2.append(response["choices"][0]["message"])
        prompt_step2.append({"role": "user", "content": "Make sure that the imports contain everything for this to compile."})


        response2 = self.prompt_executor.execute(prompt_step2).model_dump()
        new_tests = self.extract_tests(response2["choices"][0]["message"]["content"], context, response, output_path)
        if response2 is None:
            new_tests = self.extract_tests(response["choices"][0]["message"]["content"], context, response, output_path)

        chat_history.append(response2)

        # prompt_step2.append({"role": "assistant", "content": f"```java\n{new_tests}\n```"})
        # calls = re.findall(r"new (.*?)\(", new_tests, flags=re.DOTALL)
        # if calls:
        #     tree = subprocess.check_output(["tree", "-P", "*.java", "--charset=ascii", input_path]).decode("utf-8")
        #     repair_question = f"{', '.join(calls)} {'are' if len(calls) > 1 else 'is'} 'new', check if there are missing imports and fix them using this directory structure:\n```\n{tree}\n```"
        #     prompt_step2.append({"role": "user", "content": repair_question})
        #
        #     chat_history.append(prompt_step2)
        #     repair_response = self.prompt_executor.execute(prompt_step2).model_dump()
        #     chat_history.append(repair_response)
        #
        #     new_tests = self.extract_tests(repair_response["choices"][0]["message"]["content"], context, repair_response, output_path)

        #print(check_syntax(new_tests, "class", output_path))

        return new_tests, chat_history



    def build_tests(self, context, primer=""):
        packg_declaration = f"package {context['test_package']};\n\n"
        imports = "".join(context["test_imports"]) + "\n" + "// add all necessary imports here\n\n"

        for import_ in context["test_imports"]:
            if ("junit.framework") in import_:
                self.is_three = True
                break

        name = str(context["signature"]["name"])
        class_name = context["test_file_path"].split("/")[-1].split(".")[0]
        if self.is_three:
            classdefinition = "public class " + class_name + " extends TestCase {"
            test_suite_method = "\n    public"  + class_name + "(String name) {\n        super(name);\n    }\n\n    public static Test suite() {\n        return new TestSuite(" + class_name + ".class);\n    }\n"

            classdefinition = classdefinition + test_suite_method

            functions = ""
            for test in context["test_list"]:
                functions += "\n    public void " + test["test_name"] + "(){" + "\n        // " + test["test_description"] + "\n    }\n\n"

        else:
            classdefinition = "public class " + class_name + "{"

            functions = ""

            for test in context["test_list"]:
                functions += "\n    @Test\n    public void " + test["test_name"] + "(){" + "\n        // " + test["test_description"] + "\n    }\n\n"

        return packg_declaration + imports + classdefinition + functions + "\n}"



    def extract_tests(self, new_tests, context, response, output_path):
        code_blocks = re.findall(r"```java(.*?)\n\s*```", new_tests, flags=re.DOTALL)

        if code_blocks:
            new_tests = code_blocks[0]
        else:
            print("no codeblock extracted")
            new_tests = None

        # new_tests = self.try_to_fix(new_tests, response, context, output_path)   # prbably not needed

        return new_tests