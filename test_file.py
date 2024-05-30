from cascade.extraction.HumanEvalIncoExtraction import HumanEvalIncoExtraction

from cascade.generation.test.GPT4TestGenerator import GPT4TestGenerator

# test pipeline



in_path = "/home/kiecketo/repos/HE/HumanEvalInco.json"
out_path = ""


json_extr = HumanEvalIncoExtraction()

data = json_extr.extract(in_path, out_path)

print(GPT4TestGenerator(dummy=True).build_prompt(data[10]))

