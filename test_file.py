import gzip
import json

data = []
file_path = "./tests/test_resources/humanevaltest/HumanEval.jsonl.gz"

with gzip.open(file_path, "rt") as file:
    for line in file:
        data.append(json.loads(line))


for d in data:
    if "import" in d["test"]:
        print(d["task_id"])
        print(d["test"].replace("\n" , ""))

print(data[8]["test"])
