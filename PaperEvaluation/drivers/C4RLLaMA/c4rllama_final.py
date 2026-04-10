import os
import nvitop
import time
import sys
import fire
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import pandas as pd
import json
from tqdm import tqdm
from utils.prompter import Prompter
from sklearn.metrics import recall_score, precision_score, accuracy_score
import re
from utils.preprocess import parse_javadoc, clean_javadoc

def build_signature(method_context, doc=False):
    doc_string = method_context["doc"] if doc else ""
    ctsig = method_context["signature"]

    return doc_string + (" ".join(ctsig["modifier"]) + " " + ('<' + ', '.join(ctsig["generics"]) + '> ' if ctsig["generics"] else '') +
           ctsig["returns"] + " " + ctsig["name"] + "(" + ", ".join(ctsig["params"]) + ")" +
           (" throws " + ", ".join(ctsig["exceptions"]) if ctsig.get("exceptions") else ""))


if torch.cuda.is_available():
    device = "cuda"
    print("cuda")
else:
    device = "cpu"


post_instruction = """Is the given code consistent with the corresponding {}?
```code
{}
```
```{}
{}
```
"""

def main(
    base_model: str = "",
    lora_weights: str = "",
    prompt_template: str = "llama",
):
    print("base_model", base_model)

    base_model = base_model or os.environ.get("BASE_MODEL", "")
    assert (
        base_model
    ), "Please specify a --base_model, e.g. --base_model='huggyllama/llama-7b'"

    prompter = Prompter(prompt_template)
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    if device == "cuda":
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        print("2.2")
        if lora_weights:
            lora_model = PeftModel.from_pretrained(
                model,
                lora_weights,
                torch_dtype=torch.float16,
            )
        print("2.3")
    else:
        model = AutoModelForCausalLM.from_pretrained(
            base_model, low_cpu_mem_usage=True
        )
        if lora_weights:
            lora_model = PeftModel.from_pretrained(
                model,
                lora_weights,
            )

    if lora_weights:
        model = lora_model

    print("4")

    model.config.pad_token_id = tokenizer.pad_token_id = 0
    if lora_weights:
        lora_model.config.pad_token_id = 0

    model.eval()
    if torch.__version__ >= "2" and sys.platform != "win32":
        model = torch.compile(model)
    
    print("5")
  

    @torch.inference_mode()
    def evaluate(
        model,
        instruction,
        input=None,
        top_p=0.95,
        top_k=50,
        num_beams=1,
        max_new_tokens=512,
        **kwargs,
    ):
        print("6")
        prompt = prompter.generate_prompt(instruction, input)
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(device)

        with torch.no_grad():
            generation_output = model.generate(
                input_ids=input_ids,
                do_sample=True,
                top_p=top_p,
                top_k=top_k,
                num_beams=num_beams,
                return_dict_in_generate=True,
                output_scores=True,
                max_new_tokens=max_new_tokens,
            )
        s = generation_output.sequences[0]
        output = tokenizer.decode(s)
        res = prompter.get_response(output)
        return res

    try:
        with open("./analyzed.json") as f:
            data = json.load(f)
       

        sample = data[0]
        print("testing:" , sample["signature"]["name"] )
        
        full_code = build_signature(sample) + " " + sample["code"]
        


        instructions = []
        results = []

        # first result will be the docuemntation as is:  second will be everthing put into one line without the /* etc.  
        # the rest will be results for single lines according to the panthaplakel dataset namely:  summary(first sentence of the doc) param tags and return tag.

        instruction = post_instruction.format("docstring", full_code, "docstring", doc) 
        instructions.append(instruction)

        
        clean_doc = clean_javadoc(sample["doc"]) 
        instr = post_instructions.format("docstring", full_code, "docstring", doc)
        instructions.append(instr)

        
        parsed_doc = parse_javadoc(sample["doc"])
        with open("./log.txt", "a") as log:
            log.write("parsed_doc:\n")
            log.write(str(parsed_doc))
            log.write("---------------")
        
        if parsed_doc["summary"]:
            instr = post_instruction("summary", full_code, "summary", parsed_doc["summary"])
            instructions.append(instr)
        
        for k, v in parsed_doc["params"].keys()
            param = "@param " + p + " " + v
            instr = post_instruction("param", full_code, "param", param)
            instructions.append(instr)
        
        if parsed_doc["returns"]:
            instr = post_instruction("return", full_code, "return", parsed_doc["returns"])
            instructions.append(instr)
    


        # run all:
        for i in instructions:
            try:    
                with open("./log.txt", "a") as log:
                    log.write("instruction:\n")
                    log.write(str(i))
                    log.write("----")
            
                print("eval:\n", str(i))
                res = evaluate(model, i)
        
                judge = 1 if "inconsisten" in res else 0    #sic!
                prediction = "Positive" if judge == 1 else "Negative"
                results.append(prediction)
        
                print("Prediction:", prediction)

                with open("./log.txt", "a") as log:
                    log.write("result:\n")
                    log.write(str(res))
 
            except Exception as e:
                print("error:")
                with open("./log.txt" , "a") as log:
                    log.write("Error:\n")
                    log.write(str(e))
                    log.write("---")
                results.append("Error")

        lblres = "Negative"
        for r in results[2:]:
            if r == "Positive":
                lblres = "Positive"
                break

        
        with open("./result.txt", "w") as f:
            r = f"{results[0]};{results[1]};{lblres}"
            f.write("; ".join(results))


    except Exception as e:
        with open("./log.txt" , "a") as log:
            log.write("Big Error:\n")
            log.write(str(e))


if __name__ == "__main__":
    fire.Fire(main)


