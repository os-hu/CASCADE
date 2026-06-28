import os
import json
import ast
import re
import subprocess


def build_context(context, doc=False, imports = False, no_fields=False, no_other_method_docs=False , no_other_methods=False, no_constructors=False):
    generics = context["parent"]["generics"]
    implements = context["parent"]["implements"]
    extends = context["parent"]["extends"]
    constructors = context["parent"]["constructors"] if not no_constructors else []
    fields = context["parent"]["variables"] if not no_fields else []
    imports_ = context["parent"]["imports"]
    class_ = (f"{''.join(imports_) + '\n' if imports else ''}"
              f"public class {context['parent']['name']}"
              f"{('<' + ', '.join(generics) + '>' + ' ' if generics else '')}" 
              f"{('extends ' + ', '.join(extends) + ' ' if extends else '')}"
              f"{('implements ' + ', '.join(implements)  + ' ' if implements else '')}{{\n"
              )
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
                         (" throws " + ", ".join(ctsig["exceptions"]) if ctsig.get("exceptions") else ""))

# Bounded cache for the parsed project index. Each extracted.json can be hundreds of MB
# once parsed, so we keep only the most-recently-used one (cleared before inserting).
_EXTRACTED_CACHE = {}


def _load_extracted(output_path):
    """Load (and cache) extracted.json from output_path. Returns None if absent/unreadable."""
    idx_path = os.path.join(output_path, "extracted.json")
    if not os.path.exists(idx_path):
        return None
    try:
        mtime = os.path.getmtime(idx_path)
    except OSError:
        mtime = None
    key = (idx_path, mtime)
    if key in _EXTRACTED_CACHE:
        return _EXTRACTED_CACHE[key]
    try:
        with open(idx_path) as f:
            data = json.load(f)
    except Exception:
        data = None
    _EXTRACTED_CACHE.clear()  # bound memory: hold at most one parsed index at a time
    _EXTRACTED_CACHE[key] = data
    return data


def build_api_context(context, output_path,
                      include_siblings=True, include_return_api=True,
                      max_constructors=4, max_subclasses=3, max_factories=3,
                      max_siblings=15, max_return_methods=12, max_packages=25, max_chars=3500):
    """
    Build a compact, static "how to use this API" block so the model writes tests that
    compile against types that actually exist, instead of guessing cross-module ones.

    Sourced from the parent class already in `context` (constructors, sibling signatures)
    plus the project index (`extracted.json` in `output_path`) when present, which adds the
    cross-class facts: subclasses/factories for an abstract receiver, the method surface of the
    return/parameter types (so the model doesn't invent methods on them), and the project's
    package set.

    `include_siblings=False` drops the receiver's sibling list, the bulkiest and lowest-value
    section, so callers can shed weight first; the return-type surface and construction facts
    survive. Returns "" when nothing useful exists.
    """
    parent = context.get("parent", {}) or {}
    receiver = parent.get("name")
    sections = []

    sig0 = context.get("signature", {}) or {}
    # Types the method returns / takes: the model needs their real method surface, not just the
    # receiver's. Filtering candidates against the project index below drops JDK types and
    # external annotations, leaving in-project types.
    _common = {"String", "Object", "Integer", "Long", "Short", "Byte", "Boolean", "Double", "Float",
               "Character", "Number", "Void", "List", "Map", "Set", "Collection", "Iterable",
               "Iterator", "Optional", "Exception", "IOException", "RuntimeException", "Throwable",
               "Class", "T", "E", "K", "V"}
    related_types = set()
    for _t in [sig0.get("returns", "")] + list(sig0.get("params", []) or []):
        for _m in re.findall(r"[A-Z][A-Za-z0-9_]+", _t or ""):
            if _m != receiver and _m not in _common:
                related_types.add(_m)

    def _clean(s):
        # drop block/line comments and collapse whitespace so constructor strings stay compact
        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.DOTALL)
        s = re.sub(r"//[^\n]*", " ", s)
        return " ".join(s.split())

    # --- how to obtain the receiver: constructors come straight from context ---
    construct = []
    for c in (parent.get("constructors") or [])[:max_constructors]:
        c = _clean(c)
        if c:
            construct.append(c)

    # load the project index once (graceful: missing/unreadable -> skip index-derived parts)
    data = _load_extracted(output_path)

    kind = parent.get("kind") or ""
    is_abstract = "interface" in kind or any("abstract" in m for m in parent.get("modifiers", []))

    packages = set()
    if data:
        subclasses, producers = [], []
        type_methods = {}
        for d in data:
            dp = d.get("parent", {}) or {}
            pkg = d.get("package")
            if pkg:
                packages.add(pkg)
            if is_abstract and receiver:
                concrete = "interface" not in (dp.get("kind") or "") \
                    and not any("abstract" in m for m in dp.get("modifiers", []))
                if concrete and (receiver in (dp.get("extends") or [])
                                 or receiver in (dp.get("implements") or [])):
                    if dp.get("name"):
                        subclasses.append(dp["name"])
            # public methods that return the receiver type -> how to produce one. Includes
            # instance-method factories (e.g. JsonFactory.createParser), which are the common
            # idiom, not just static ones.
            if receiver and dp.get("name"):
                sig = d.get("signature", {}) or {}
                mods = sig.get("modifier", [])
                if sig.get("returns") == receiver and any("public" in m for m in mods):
                    is_static = any("static" in m for m in mods)
                    is_factory = "factory" in dp["name"].lower()  # *Factory: common producer idiom
                    rendered = f'{dp["name"]}.{sig["name"]}({", ".join(sig.get("params", []))})'
                    producers.append((is_static, is_factory, rendered))
            # public method surface of the method's return/parameter types, when they are
            # project classes (so the model calls real methods on them, not invented ones)
            if include_return_api and dp.get("name") in related_types:
                msig = d.get("signature", {}) or {}
                if any("public" in m for m in msig.get("modifier", [])):
                    try:
                        type_methods.setdefault(dp["name"], []).append(build_signature(d).strip())
                    except Exception:
                        pass
        if is_abstract:
            for s in sorted(set(subclasses))[:max_subclasses]:
                construct.append(f"concrete subclass: {s}")
            # rank: factory-named classes first, then static (directly callable), then by name
            for is_static, _, fct in sorted(set(producers), key=lambda x: (not x[1], not x[0], x[2]))[:max_factories]:
                construct.append(("factory: " if is_static else "produced by (call on an instance): ") + fct)

    if construct:
        sections.append(f"How to obtain a {receiver} instance:\n  - " + "\n  - ".join(construct))

    # --- in-class sibling methods (signatures only; already present in context) ---
    # This is the bulkiest section and the first to be dropped under budget pressure.
    if include_siblings:
        siblings = []
        for other in (parent.get("other_methods") or [])[:max_siblings]:
            try:
                siblings.append(build_signature(other, doc=False).strip())
            except Exception:
                continue
        if siblings:
            sections.append(f"Other methods available on {receiver} (signatures):\n  " + "\n  ".join(siblings))

    # --- method surface of the return/parameter types; kept in the light variant (high value) ---
    if include_return_api and data:
        for tname in sorted(type_methods):
            meths, seen = [], set()
            for s in type_methods[tname]:
                if s and s not in seen:
                    seen.add(s)
                    meths.append(s)
            meths = meths[:max_return_methods]
            if meths:
                sections.append(
                    f"Methods available on {tname} (a project type used/returned by the method "
                    f"under test; call only these, do not invent others):\n  " + "\n  ".join(meths))

    # --- available-type guidance (the import-universe / cross-module fix) ---
    if packages:
        pkgs = sorted(packages)[:max_packages]
        sections.append(
            "This project only provides types in these packages: " + ", ".join(pkgs) + ".\n"
            "Only import types from these project packages or the standard JDK. Do NOT import "
            "types from other modules/libraries that are not part of this project."
        )

    if not sections:
        return ""
    block = ("API context (static facts about the available code; "
             "use only these APIs, do not invent any):\n\n" + "\n\n".join(sections))
    if len(block) > max_chars:
        block = block[:max_chars].rstrip() + "\n... (truncated)"
    return block


def check_syntax(code, type, output_path):
    """
    checks if a piece of java code (either a block or a full class) is syntactically correct
    by writing it to a temporary file and running the JavaExtractor.jar (in its verify mode) on it.
    The output is logged to log.txt in the output_path.

    :param code: the string containing the code to be checked
    :param type:   should be "block" or "class"
    :return:  True if the given code is syntactically correct, False if not.
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



def get_repair_helper_functions():
    """
    Returns the available functions that can be used for 'tool' usage of common LLM APIs (e.g. OpenAI).
    """
    def build_tool_description(name, description, parameters):
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

    t1 = build_tool_description("get_child_classes", "Gets all classes that implement or extend a given class.", [
        ("class_name", "string", "The simple name of the class for which child classes are to be retrieved"),
        ("abstract_included", "boolean", "Should abstract classes be included?")])
    t2 = build_tool_description("get_class_methods", "Gets a list of all methods from a given class.", [
        ("path_to_class", "string", "The relative path to the class"),
        ("private_included", "boolean", "Should private methods be included?")])
    t3 = build_tool_description("get_class_constructors", "Gets a list of constructors for a given class.", [
        ("path_to_class", "string", "The relative path to the class")])
    t4 = build_tool_description("get_file_content", "Gets the entire content of a specific file.", [
        ("path_to_file", "string", "The relative path to the file")])
    t5 = build_tool_description("get_class_fields", "Gets a list of fields of a given class.", [
        ("path_to_class", "string", "The relative path to the class"),])

    tools = [t1, t2, t3, t4, t5]
    return tools


def repair_helper_functions(func, arguments, input_path, output_path, context):
    arguments = json.loads(arguments)
    functions = {"get_class_methods": get_class_methods, "get_class_constructors": get_class_constructors,
                 "get_child_classes": get_child_classes, "get_file_content" : get_file_content, "get_class_fields" : get_class_fields}

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


def get_class_fields(input_path, output_path, context, path_to_class, private_included):
    with open(os.path.join( output_path ,"extracted.json"), "r") as f:
        data = json.load(f)


    returns = []

    for d in data:
        if d["code_file_path"] ==  path_to_class:
            returns = d['parent']['variables']
            break

    return { "constructors" : returns}


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



