import os
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
        file.write(p.stdout + "\n")
        file.write(p.stderr + "\n")
    os.remove("temp.java")

    if p.returncode == 0:
        return True
    else:
        return False

