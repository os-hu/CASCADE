import copy
import json
import os
import tiktoken

from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT4Executor import GPT4Executor
from cascade.utils.JavaUtils import build_context


class GPT4JavaTestGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=1000, temperature=0, delay=3, max_prompt_tokens=2000, freq_penalty=0.0, dummy=False):
        super().__init__()
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = GPT4Executor(max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature,
                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

        self.is_three = False

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model("gpt-4")

        system_prompt = f"Write Java JUnit tests for the function {context['signature']['name']}."

        code = "// CODE:\n\n" + build_context(context, doc=True)

        test_header = ";\n}\n\n// TESTS:\n\n" + self.build_tests(context, primer=f"\n    // write tests for {context['signature']['name']} here\n")

        prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True, no_constructors=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = "// CODE:\n\n" + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True,
                                 no_other_methods=True)
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return []


        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist



    def build_tests(self, context, primer=""):
        packg_declaration = f"package {context['test_package']};\n\n"
        imports = "".join(context["test_imports"]) + "\n"

        for import_ in context["test_imports"]:
            if import_.startswith("import junit.framework"):
                self.is_three = True
                break

        name = str(context["signature"]["name"])
        class_name = context["test_file_path"].split("/")[-1].split(".")[0]
        if self.is_three:
            classdefinition = "public class " + class_name + " extends TestCase {"
            test_suite_method = "\n    public static Test suite() {\n        return new TestSuite(" + class_name + ".class);\n    }\n"

            classdefinition = classdefinition + test_suite_method
            func_definition = "\n    public void test" + name[0].upper() + name[1:] + "1(){"
        else:
            classdefinition = "public class " + class_name + "{"
            func_definition = "\n    @Test\n    public void test" + name[0].upper() + name[1:] + "1(){"
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

            if context != context2:
                response = None

        if not response:
            response = self.prompt_executor.execute(prompt).model_dump()

            safety_copy = copy.deepcopy(context)
            safety_copy["response"] = response

            with open(test_safety_copy_path , "w") as file:
                json.dump(safety_copy, file)

        new_test = response["choices"][0]["message"]["content"]

        if response["choices"][0]["finish_reason"] == "length":
            new_test = self.try_to_fix(new_test)

        new_test = self.build_tests(context) + "\n" + new_test

        return new_test , response


    def try_to_fix(self, new_test):
        last_test = 0
        lines = new_test.splitlines()

        for num, line in enumerate(lines):
            if not self.is_three:
                if "@Test" in line:
                    last_test = num
            else:
                if "public void test" in line:
                    last_test = num

        return "\n".join(lines[:last_test]) + "\n}"


