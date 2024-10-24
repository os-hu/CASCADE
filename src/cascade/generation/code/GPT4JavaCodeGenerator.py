import re
from inspect import signature

from cascade.generation.Generator import Generator
from cascade.generation.executor.OpenAIChatCompletionExecutor import OpenAIChatCompletionExecutor
from cascade.utils.JavaUtils import build_context, build_signature, repair_helper_functions

import os
import copy
import tiktoken
import json

class GPT4JavaCodeGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=16000, temperature=0, delay=3, max_prompt_tokens=5000, model="gpt-4o-mini-2024-07-18", freq_penalty=0.0, dummy=False):
        super().__init__()
        self.model = model
        self.max_prompt_tokens = max_prompt_tokens
        self.prompt_executor = OpenAIChatCompletionExecutor(max_attempts=max_attempts, model=model, max_tokens=max_tokens, temperature=temperature,
                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy)

    def build_prompt(self, context):
        enc = tiktoken.encoding_for_model(self.model)

        system_prompt = f"Write the body of one Java function for {context['signature']['name']}. Follow its documentation as closely as possible. Respond only with the function"

        packg_declaration = f"package {context['package']};\n\n"

        imports = "".join(context["parent"]["imports"]) + "\n"

        code = build_context(context, doc=True)

        primer =  "{\n// write the function body here. Take the Documentation as literal as possible.\n"

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
            code = build_context(context, doc=True, no_fields=True, no_constructors=True,  no_other_method_docs=True, no_other_methods=True)
            prompt = code + primer

        if len(enc.encode(prompt)) > self.max_prompt_tokens:
            return []


        promptlist = []
        promptlist.append({"role": "system", "content": system_prompt})
        promptlist.append({"role": "user", "content": prompt})

        return promptlist


    def generate(self, context, input_path, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)

        if not prompt:
            return "", None

        response = self.prompt_executor.execute(prompt).model_dump()

        response = {"prompt": prompt, "response": response}

        new_code = response["response"]["choices"][0]["message"]["content"]

        new_code = self.extract_code(new_code, context, response["response"], output_path)

        return new_code , response



    def extract_code(self, new_code, context, response, output_path):
        code_blocks = re.findall(r"```java(.*?)\n```", new_code, flags=re.DOTALL)

        if code_blocks:
            new_code = code_blocks[0]
        else:
            new_code = new_code.split("```java")[-1].strip()

        return self.try_to_fix(new_code, context, response)


    def try_to_fix(self, new_code, context, response):
        temp = new_code.split(build_signature(context , False))
        if len(temp) > 1:
            new_code = "".join(temp[1:])
            new_code = new_code[new_code.find("{") + 1:]


        fixed_code = ""
        # First brace is already there
        braces = 1
        for letter in new_code:
            if letter == "{":
                braces += 1
            elif letter == "}":
                braces -= 1
            if braces == 0:
                break
            fixed_code += letter

        return "{" + fixed_code + "}"


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
        t4 = build_tool("get_file_content", "Gets the content of a specific file.", [
            ("path_to_file", "string", "The relative path to the file")])

        tools = [t1,t2,t3, t4]

        system_prompt = "You are a Java developer assistant. Fix compilation errors in the provided code. Use tools to find out more about classes instead of making assumptions."

        prompt = f"The following errors occurred during compilation of class {context["parent"]["name"]}.\n```\n{errors}\n```\n Fix the errors in the following function:\n```java\n{build_signature(context, doc=True) + context[key]}\n```"

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

                results = repair_helper_functions(func, arguments, input_path, output_path, context)

                promptlist.append({"role": "tool", "content": json.dumps(results), "tool_call_id": tool_call["id"]})

            res = self.prompt_executor.execute(promptlist).model_dump()



        repair_response = {"prompt": promptlist, "response": res}

        new_code = res["choices"][0]["message"]["content"]

        new_code = self.extract_code(new_code, context, res, output_path)

        return new_code, repair_response





