import sys
import os
import gzip
import json
from src import Utils

from src.abstract_classes.Extraction import Extraction
class Human_Eval_Basic_Extraction(Extraction):
    """
    An implementation of the abstract "Extraction" class.
    This is designed to extract the Basic 164 functions from the HumanEval dataset provided in its basic json format.
    See extract() method for details.
    """
    def __init__(self):
        pass

    def extract(self, input_path, output_path, printmode=False) -> dict:
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

        It also parses the very simplistic tests from HumaneEval into Python unittest classes.

        :param input_path: should be a path to a file which contains the human eval dataset (or a subset of it.) either
        in json, (jsonl) or a .gz containing a json file
        Can also be a path to a folder containing one file only then this is read in.
        # TODO read in all files?

        :param output_path: the extracted dataset is saved as a temporary json file called "extracted.json"
        in this specified folder.
        if the path contains a filename (ends in ".json") this name is chosen instead.

        :return: a dictionary
        """

        if printmode: print(f"starting to extract from: {input_path}")

        # check if the path is to a file or to a folder
        if os.path.isdir(input_path):
            # List all files in the directory
            files = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]


            # Check if there is exactly one file
            if len(files) == 1:
                file_path = os.path.join(input_path, files[0])

            elif len(files) == 0:
                raise FileNotFoundError("there is no file in this folder")
            else:
                raise FileNotFoundError("there is more than one file in the folder")

        elif os.path.isfile(input_path):
            file_path = input_path

        else:
            raise FileNotFoundError(f"could not find folder or file {input_path}")


        allowed_extensions = (".json",".jsonl",".gz")
        if not file_path.endswith(allowed_extensions):
            raise FileNotFoundError("found no json or gz file")


        else:
            data = []
            if file_path.endswith(".gz"):
                with gzip.open(file_path, "rt") as file:
                    for line in file:
                        data.append(json.loads(line))

            else:
                with open(file_path, 'r') as file:
                    for line in file:
                        data.append(json.loads(line))

        if printmode: print(f"extracted {len(data)} entries")


        # save the extracted dictionaries

        print(file_path)
        print(os.path.dirname(file_path))

        #if printmode: print(f"saved to: {output_file_path}")