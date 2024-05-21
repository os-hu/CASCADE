import json
import os
import shutil
import subprocess

from src.utils.Utils import load_json_from_path


def build_project(context, in_path, out_path, code, tests):
    result = ([], [], [])


    try:
        shutil.copytree(in_path, out_path, dirs_exist_ok=True)

    except Exception as e:
        print("could not copy root path")
        print(e)

    entry = os.path.join(out_path, "entry.json")
    with open(entry, "w") as json_entry:
        json.dump(context, json_entry)

    my_path = os.path.dirname(__file__)
    p = subprocess.run(
        ["java", "-jar", os.path.join(my_path, "..", "resources", "tools", "JavaModifier.jar"),
         out_path,
         entry,
         code,
         tests],
        capture_output=True,
        text=True
    )

    os.remove(entry)


if __name__ == '__main__':
    # load the json
    analyzed_path = "/home/kiecketo/analyzed.json"
    in_path = "/home/kiecketo/repos/commons-lang/"
    out_path = "/home/kiecketo/PycharmProjects/CASCADE/eval/commons-lang2/"
    id = 106

    code = "new_code"
    tests = "new_tests"


    data = load_json_from_path(analyzed_path)

    context = next(item for item in data if item["id"] == id)
    print(context["package"], context["parent"]["name"])
    print(context["signature"])
    #print(context["new_code_response"])

    build_project(context, in_path, out_path, code, tests)
