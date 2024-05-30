


def build_signature(context, doc=False):
    imports = "\n".join(context["parent"]["imports"])
    imports = imports + "\n"
    imports = imports + "\n".join(context["parent"]["other_methods"])

    name = context["signature"]["name"]
    para = context["signature"]["params"]

    if len(para) > 1:
        param_string = ", ".join(para)
    else:
        param_string = para[0] if len(para) == 1 else ""

    returns = context["signature"]["returns"]
    signature = f"def {name}({param_string})" + (" -> " + returns if returns else "") + ":"

    doc = f"\"\"\"\n{context['doc']}\n\"\"\""
    doc = "\n".join("    " + line for line in doc.splitlines())

    return "\n".join([imports, signature, doc])