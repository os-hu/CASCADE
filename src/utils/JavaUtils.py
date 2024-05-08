def build_context(context, doc=False, no_fields=False, no_other_methods=False):
    generics = context["parent"]["generics"]
    implements = context["parent"]["implements"]
    extends = context["parent"]["extends"]
    constructors = context["parent"]["constructors"]
    fields = context["parent"]["variables"]
    class_ = f"public class {context['parent']['name']}{('<' + ', '.join(generics) + '>' + ' ' if generics else '')} {('extends ' + ', '.join(extends) + ' ' if extends else '')}{('implements ' + ', '.join(implements)  + ' ' if implements else '')}{{\n"

    field_string = "\n".join(fields) + "\n"

    constructor_string = "\n".join(constructors) + "\n"

    other_methods = ""
    for other in context["parent"]["other_methods"]:
        other_methods += build_signature(other) + ";\n"

    signature = build_signature(context, doc)

    sig = class_ + field_string + constructor_string + other_methods + signature

    return sig

def build_signature(method_context, doc=False):
    doc_string = method_context["doc"] if doc else ""
    ctsig = method_context["signature"]
    return doc_string + (" ".join(ctsig["modifier"]) + " " + ('<' + ', '.join(ctsig["generics"]) + '>' if ctsig["generics"] else '') +
                 ctsig["returns"] + " " + ctsig["name"] + "(" + ", ".join(ctsig["params"]) + ")")
