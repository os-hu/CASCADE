import os
import json
import ast
import subprocess


def build_context(context, doc=False, no_fields=False, no_other_method_docs=False , no_other_methods=False, no_constructors=False):
    generics = context["parent"]["generics"]
    implements = context["parent"]["implements"]
    extends = context["parent"]["extends"]
    constructors = context["parent"]["constructors"] if not no_constructors else []
    fields = context["parent"]["variables"] if not no_fields else []
    class_ = f"public class {context['parent']['name']}{('<' + ', '.join(generics) + '>' + ' ' if generics else '')} {('extends ' + ', '.join(extends) + ' ' if extends else '')}{('implements ' + ', '.join(implements)  + ' ' if implements else '')}{{\n"

    field_string = "\n".join(fields) + "\n"

    constructor_string = "\n".join(constructors) + "\n"

    other_methods = ""
    for other in (context["parent"]["other_methods"] if not no_other_methods else []):
        other_methods += build_signature(other, doc=(not no_other_method_docs)) + ";\n"

    signature = build_signature(context, doc)

    sig = class_ + field_string + constructor_string + other_methods + signature

    return sig


def build_signature(method_context, doc=False):
    doc_string = method_context["doc"] if doc else ""
    ctsig = method_context["signature"]

    return doc_string + (" ".join(ctsig["modifier"]) + " " + ('<' + ', '.join(ctsig["generics"]) + '> ' if ctsig["generics"] else '') +
                 ctsig["returns"] + " " + ctsig["name"] + "(" + ", ".join(ctsig["params"]) + ")" +
                         (" throws " + ", ".join(ctsig["exceptions"]) if ctsig["exceptions"] else ""))

def check_syntax(code, type, output_path):
    """

    :param code:
    :param type:   should be "block" or "class"
    :return:
    """
    with open("temp.java", "w") as file:
        file.write(code)

    my_path = os.path.dirname(__file__)
    p = subprocess.run(
        ["java", "-jar", os.path.join(my_path, "..", "resources", "tools", "JavaExtractor.jar"),
         "ver",
         type,
         "temp.java",
         ],
        capture_output=True,
        text=True
    )
    with open(os.path.join(output_path, "log.txt"), "a") as file:
        file.write("verify returned with:" + str(p.returncode))
        file.write(code + "\n")
        file.write(p.stdout + "\n")
        file.write(p.stderr + "\n")
    os.remove("temp.java")

    if p.returncode == 0:
        return True
    else:
        return False


def repair_helper_functions(func, arguments, input_path, output_path, context):
    arguments = json.loads(arguments)
    functions = {"get_class_methods": get_class_methods, "get_class_constructors": get_class_constructors,
                 "get_child_classes": get_child_classes, "get_file_content" : get_file_content}

    try:
        return functions[func](input_path, output_path, context, **arguments)
    except:
        return {}

def get_file_content(input_path, output_path, context, path_to_file):
    if path_to_file in [context["test_file_path"], context["code_file_path"]]:
        return  { "content" : "" , "error" : "path prohibited" }

    path = os.path.join( input_path, path_to_file)
    if os.path.exists(path):
        with open(path, "r") as f:
            return {"content" : f.read()}
    else:
        return {"content" : "", "error" : "file does not exist"}


def get_class_methods(input_path, output_path, context, path_to_class, private_included):
    with open(os.path.join( output_path ,"extracted.json"), "r") as f:
        data = json.load(f)

    returns = []

    for d in data:
        if d["code_file_path"] == path_to_class and (private_included or "private" not in d["signature"]["modifier"]):
            returns.append(build_signature(d))

    return { "methods" : list(returns)}


def get_class_constructors(input_path, output_path, context, path_to_class):
    with open(os.path.join( output_path ,"extracted.json"), "r") as f:
        data = json.load(f)


    returns = []

    for d in data:
        if d["code_file_path"] ==  path_to_class:
            returns = d['parent']['constructors']
            break

    return { "constructors" : returns}


def get_child_classes(input_path, output_path, context, class_name, abstract_included):
    with open(os.path.join( output_path ,"extracted.json"), "r") as f:
        data = json.load(f)

    returns = set()

    for d in data:
        if abstract_included or ("interface" not in d["parent"]["kind"] and "abstract" not in d["parent"]["modifiers"]):
            if class_name in d["parent"]["implements"] or class_name in d["parent"]["extends"]:
                returns.add(d["code_file_path"])

    return { "child_classes" : list(returns)}



