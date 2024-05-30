from cascade.generation.Generator import Generator
from cascade.generation.executor.GPT35CompletionExecutor import GPT35CompletionExecutor
from cascade.utils.PythonUtils import build_signature

import os
import copy


class GPT35DocGenerator(Generator):
    def __init__(self, max_attempts=1, max_tokens=800, temperature=0, delay=3):
        super().__init__()
        self.prompt_executor = GPT35CompletionExecutor(max_attempts=max_attempts, max_tokens=max_tokens,
                                                       temperature=temperature, delay=delay)

    def build_prompt(self, context):
        setup = "# SETUP: Write functional correct python code.\n\n"
        sig_and_doc = build_signature(context, doc=True)
        prompt = setup + sig_and_doc

        return prompt
        return [{"role": "user", "content": prompt}]

    def generate(self, context, output_path, safety_copy_prefix):
        prompt = self.build_prompt(context)
        print(prompt)
        response = self.prompt_executor.execute(prompt).model_dump()

        savety_copy = copy.deepcopy(context)
        savety_copy["response"] = response
        #save_dicts_list_to_json([savety_copy], os.path.join(output_path, "code_generator_current.json"))



        with open(os.path.join(output_path, safety_copy_prefix + "doc_generator_current.json") , "w") as file:
            file.write(str(savety_copy))


        new_code = response["choices"][0]["text"]

        return(new_code , response)
