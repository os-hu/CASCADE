def build_signature(context, doc=False):


    generics = context["parent"]["generics"]
    implements = context["parent"]["implements"]
    extends = context["parent"]["extends"]
    constructors = context["parent"]["constructors"]
    class_ = f"public class {context['parent']['name']}{('<' + ', '.join(generics) + '>' + ' ' if generics else '')} {('extends ' + ', '.join(extends) + ' ' if extends else '')}{('implements ' + ', '.join(implements)  + ' ' if implements else '')}{{\n"

    constructor_string = "\n".join(constructors)
    doc_string = context["doc"] if doc else ""

    ctsig = context["signature"]
    signature = (" ".join(ctsig["modifier"]) + " " + ('<' + ', '.join(ctsig["generics"]) + '>' if generics else '') +
                 ctsig["returns"] + " " + ctsig["name"] + "(" + ", ".join(ctsig["params"]) + ")")


    sig = class_ + constructor_string + doc_string + signature

    return sig