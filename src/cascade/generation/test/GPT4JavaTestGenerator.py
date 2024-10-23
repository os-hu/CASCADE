import copy
import json
import os
import re
import subprocess
from platform import system

import tiktoken

from cascade.generation.Generator import Generator
from cascade.generation.executor.OpenAIChatCompletionExecutor import OpenAIChatCompletionExecutor
from cascade.utils.JavaUtils import build_context, check_syntax, repair_helper_functions


class GPT4JavaTestGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=10000, temperature=0, delay=3, max_prompt_tokens=5000, model="gpt-4o-mini-2024-07-18", freq_penalty=0.0, dummy=False, ask_for_imports=False, import_prompt_finisher="Reply with the missing imports, leave out those you don't know the correct package of."):
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
            testframework = "Use JUnit version " + (version if version[0].isdigit() else "5" )


        par = context['signature']['params']
        params = ", ".join(par) if len(par) > 1 else (par[0] if par else "")

        #system_prompt = f"Write Java tests for the function {context['signature']['name']}. Follow its documentation as closely as possible."
        system_prompt = f"You are a Java developer assistant. Generate unit tests for the function `{context['signature']['name']}({params})` in the provided class, using only its documentation. {testframework}. You can import anything from the project, but no third party libraries. Handle exceptions properly, and ensure method signatures and calls are correct. The code should compile without errors." #Use only standard Java libraries and do not import any external or third-party packages. Ensure all code is compilable and follows best practices."

        c1 = "Here is the class containing the function:\n\n```java\n"
        c2 = "{\n    // this is the function to be tested\n;\n}\n```\n"
        code = c1 + build_context(context, doc=True) + c2

        #test_header = "\n\n// TESTS:\n\n" + self.build_tests(context, primer=f"\n    // write tests for {context['signature']['name']} here. Take the Documentation as literal as possible.\n")

        test_header = f"\nNow Please write tests for the function `{context['signature']['name']}({params})` using the following test class skeleton.  Everything that you use should be added to the imports in the skeleton. Properly handle any checked exceptions (use `try-catch` or `throws`), don't forget type parameters. Match method signatures exactly when overriding or implementing methods. Adhere to the documentation as close as possible when writing the tests. As a reminder, the documentation for the function is:\n\n```java\n{context['doc']}\n```\nand here is the test class\n"
        test_header = test_header + "\n```java\n" + self.build_tests(context, primer=f"\n    // write tests for {context['signature']['name']} here." + "\n```")

        if self.is_three:
            test_header = test_header
            # add something like:    Include necessary constructors if extending a class that requires them.


        prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True) + c2
            prompt = code + test_header

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            code = c1 + build_context(context, doc=True, no_fields=True, no_constructors=True, no_other_method_docs=True,
                                                  no_other_methods=True) + c2
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
            if ("junit.framework") in import_:
                self.is_three = True
                break

        name = str(context["signature"]["name"])
        class_name = context["test_file_path"].split("/")[-1].split(".")[0]
        if self.is_three:
            classdefinition = "public class " + class_name + " extends TestCase {"
            test_suite_method = "\n    public"  + class_name + "(String name) {\n        super(name);\n    }\n\n    public static Test suite() {\n        return new TestSuite(" + class_name + ".class);\n    }\n"

            classdefinition = classdefinition + test_suite_method
            func_definition = "\n    public void test" + name[0].upper() + name[1:] + "1(){"
        else:
            classdefinition = "public class " + class_name + "{"
            func_definition = "\n    @Test\n    public void test" + name[0].upper() + name[1:] + "1(){"
        return packg_declaration + imports + classdefinition + primer + func_definition


    def generate(self, context, input_path, output_path, safety_copy_prefix):
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

            imports = dict()

            text = response["choices"][0]["message"]["content"]

            # extract all 'new' statements.
            calls = re.findall(r"new (.*?)\(", text, flags=re.DOTALL)

            tree = subprocess.check_output(["tree", "-P", "*.java", input_path]).decode("utf-8")

            repair_question = f"{', '.join(calls)} are new, fix all missing imports using this directory structure:\n```\n{tree}\n```"

            prompt.append({"role" : "user", "content" : repair_question})

            repair = self.prompt_executor.execute(prompt)

            repair = repair.model_dump()

            # if self.ask_for_imports or (len(context["test_imports"]) == 1 and "*" in context["test_imports"][0]):
            #     prompt.append({"role" : "assistant", "content" : response["choices"][0]["message"]["content"]})
            #     prompt.append({"role" : "user", "content" : f"Give me the missing imports for this code to work. For the tests, I am already importing:\n```java\n{''.join(context['test_imports'])}\n```\n\n The tested class imports:\n```java\n{''.join(context['parent']['imports'])}\n```\n\n{self.import_prompt_finisher}" })
            #     imports = self.prompt_executor.execute(prompt).model_dump()
            #     imports_message = imports["choices"][0]["message"]["content"]
            #     for line in imports_message.splitlines():
            #         if "import" in line and ";" in line:
            #             context["test_imports"].append(line + "\n")
            #     context["test_imports"] = list(set(context["test_imports"]))

            response = {"prompt" : prompt, "response" : response, "repair" : repair ,  "imports" : imports}
            safety_copy["response"] = response
            with open(test_safety_copy_path , "w") as file:
                json.dump(safety_copy, file)

        # TODO WRONG RESPONSE
        new_tests = response["repair"]["choices"][0]["message"]["content"]

        new_tests = self.extract_tests(new_tests, context, response, output_path)

        return new_tests , response


    def extract_tests(self, new_tests, context, response, output_path):
        code_blocks = re.findall(r"```java(.*?)\n```", new_tests, flags=re.DOTALL)

        if not code_blocks == []:
            new_tests = code_blocks[0]
        else:
            new_tests = new_tests.split("```java")[-1].strip()

        new_tests = self.try_to_fix(new_tests, response, context, output_path)

        return new_tests



    def try_to_fix(self, new_tests, response, context, output_path):
        # check if the class is complete
        chunk = ""
        braces = 2
        for letter in new_tests:
            chunk += letter
            if letter == "{":
                braces += 1
            elif letter == "}":
                braces -= 1
            if braces == 0:
                break

        # we have to complete the class
        if braces == 0:
            return self.build_tests(context) + chunk

        if braces == 1:
            # two possible cases  full class with a brace too much   or a completion with a brace to few
            #full class
            to_check = [chunk[:chunk.rfind("}")], self.build_tests(context) + chunk + "}", self.build_tests(context) + chunk[chunk.find("{") + 1:]]
            for check in to_check:
                if check_syntax(check, "class", output_path):
                    return check

        # the class is complete
        if braces == 2:
            check = chunk
            if check_syntax(check, "class", output_path):
                return check   # TODO This seems to be the grand majority now.
            check = self.build_tests(context) + chunk[chunk.find("{") + 1:] + "}"
            if check_syntax(check, "class", output_path):
                return check


        if braces > 2:
            if response['response']['choices'][0]["finish_reason"] == "length":
                last_test = 0
                lines = new_tests.splitlines()

                for num, line in enumerate(lines):
                    if not self.is_three:
                        if "@Test" in line:
                            last_test = num
                    else:
                        if "public void test" in line:
                            last_test = num

                return "\n".join(lines[:last_test]) + "\n}"

        return new_tests + "}"*(braces-2)


    def repair(self, context, input_path, output_path, errors, key):
        def build_tool(name, description, parameters):
            return {"type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "strict": True,
                        "parameters": {
                            "type": "object",
                            "required": [
                                *map(lambda x: x[0], parameters)
                            ],
                            "properties": {
                                **{x[0]: {"type": x[1], "description": x[2]} for x in parameters}
                            },
                            "additionalProperties": False
                        }
                    }}

        t1 = build_tool("get_child_classes", "Gets all classes that implement or extend a given class.", [
            ("class_name", "string", "The simple name of the class for which child classes are to be retrieved"),
            ("abstract_included", "boolean", "Should abstract classes be included?")])
        t2 = build_tool("get_class_methods", "Gets a list of all methods from a given class.", [
            ("path_to_class", "string", "The relative path to the class"),
            ("private_included", "boolean", "Should private methods be included?")])
        t3 = build_tool("get_class_constructors", "Gets a list of constructors for a given class.", [
            ("class_name", "string", "The simple name of the class for which child classes are to be retrieved")])

        tools = [t1,t2,t3]

        # TODO could be excluded into a tool call as well?
        tree = subprocess.check_output(["tree", "-P", "*.java", input_path]).decode("utf-8")

        system_prompt = "You are a Java developer assistant. Fix the following errors in the provided unit test class. Use tools to find out more about classes instead of making assumptions."

        prompt = f"The following errors occurred during compilation.\n```\n{errors}\n```\n This is the project structure \n```\n{tree}\n```\n Please fix the errors in the following test class:\n```java\n{context[key]}\n```"

        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        res = self.prompt_executor.execute(promptlist, tools=tools).model_dump()

        if res["choices"][0]["finish_reason"] == "tool_calls":
            promptlist.append(res['choices'][0]['message'])

            tool_calls = res["choices"][0]["message"]["tool_calls"]

            for tool_call in tool_calls:
                func = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                results = {}
                # make funciton call
                results = repair_helper_functions(func, arguments, input_path, output_path)

                promptlist.append({"role": "tool", "content": json.dumps(results), "tool_call_id": tool_call["id"]})

            res = self.prompt_executor.execute(promptlist).model_dump()



        repair_response = {"prompt": promptlist, "response": res}

        new_tests = res["choices"][0]["message"]["content"]

        new_tests = self.extract_tests(new_tests, context, res, output_path)

        return new_tests, repair_response

