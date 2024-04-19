from src.abstract_classes.Code_Generator import Code_Generator
from src.implementations.generation.prompt_executor.GPT35Completion_Prompt_Executor import GPT35Completion_Prompt_Executor
from src.utils.Python_Utils import  build_signature
from src.utils.Utils import save_dicts_list_to_json

import os
import copy


class GPT35_Code_Generator(Code_Generator):
    def __init__(self, api_key_path, max_attempts=1, max_tokens=800, temperature=0, delay=3):
        self.prompt_executor = GPT35Completion_Prompt_Executor(api_key_path, max_attempts=max_attempts, max_tokens=max_tokens, temperature=temperature, delay=delay)

    def build_prompt(self, context):
        setup = "# SETUP: Write functional correct python code.\n\n"
        sig_and_doc = build_signature(context, doc=True)
        prompt = setup + sig_and_doc

        return prompt
        return [{"role": "user", "content": prompt}]

    def generate(self, context, output_path):
        prompt = self.build_prompt(context)
        print(prompt)
        response = self.prompt_executor.generate(prompt).model_dump()

        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response
        #save_dicts_list_to_json([savety_copy], os.path.join(output_path, "code_generator_current.json"))



        with open(os.path.join(output_path, "code_generator_current.json") , "w") as file:
            file.write(str(savety_copy))


        new_code = response["choices"][0]["text"]

        return(new_code , response)
