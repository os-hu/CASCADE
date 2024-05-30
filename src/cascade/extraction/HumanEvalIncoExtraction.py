import ast
import json

from cascade.extraction.Extraction import Extraction


class HumanEvalIncoExtraction(Extraction):
    """
    An implementation of the abstract "Extraction" class.
    This is designed to extract the HumanEvalInco dataset and choose which parts of it to use. especially in regards to
    inconsistencies and usage examples.
    """
    def __init__(self, doc_modifier="wuni") -> object:
        super().__init__()
        self.doc_modifier = doc_modifier

    class AssertTransformer(ast.NodeTransformer):
        """
        this class is used to visit asserts in the test methods and convert them into corresponding unittest classes.

        it was partially written with the help of chatGPT

        """

    def extract(self, input_path, output_path) -> list[dict]:
        """
        nuni - no usage examples, no inconsistencies
        wuni - with usage examples, no inconsistencies
        nuwi - no usage examples, with inconsistencies
        wuwi - with usage examples, with inconsistencies
        one of these modifiers should be passed to the constructor of this class. the corresponding type of doc is then set for all elements of the dataset


        """

        if self.doc_modifier not in ["nuni", "wuni", "nuwi", "wuwi"]:
            raise ValueError("Invalid doc modifier")

        with open(input_path, "r") as file:
            data = json.load(file)

        for entry in data:
            if self.doc_modifier in ["nuwi", "wuwi"]:
                entry["inco_type"] = entry["doc"]["changes"]
            entry["doc"] = entry["doc"][self.doc_modifier]

        return data
