import sys

from src.abstract_classes.Extraction import Extraction
class Human_Eval_Basic_Extraction(Extraction):
    """
    An implementation of the abstract "Extraction" class.
    This is designed to extract the Basic 164 functions from the HumanEval dataset provided in its basic json format.
    See extract() method for details.
    """
    def __init__(self):
        pass

    def extract(self, input_path, output_path) -> dict:
        """
        This method is used to extract the HumanEval Dataset from a json file.
        The format of the json objects in the file should be:

        {
            "task_id": a string, usually: 'HumanEval/xy'
            "prompt": a string containing the generation prompt. usually imports followed
                by the function definition and the docstring
            "entry_point": the starting point for the generation, usually the function name
            "canonical_solution": the body of the function containing a possible solution correct implementation
                of the behavior explained in the docstring
            "test": a test function filled with asserts, called check(candidate) in a string. usually preceded
                by a dictionary called METADATA.
        }

        The output is the dictionary as described in the abstract super class "Extraction"



        it also parses the very simplistic tests from HumaneEval into Python unittest classes.



        the format of the json objects in the file should be:


        :param input_path: should be a path to a file which contains the human eval dataset (or a subset of it.)
        Can also be a path to a folder containing several json file that are then ALL read in.

        :param output_path: the extracted dataset is saved as a temporary json file called "extracted.json"
        in this specified folder.
        if the path contains a filename (ends in ".json") this name is chosen instead.

        :return: a dictionary
        """
        pass

        # end in jsonl  support

        # end in json support

        # end in gz support
