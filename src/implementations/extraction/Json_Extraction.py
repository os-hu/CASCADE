from src.abstract_classes.Extraction import Extraction
from typing import List, Dict, Optional
from src.Utils import load_json_from_path
import os

class Json_Extraction(Extraction):
    """
    TODO
    """
    def extract(self, input_path, output_path) -> List[Dict[str, any]]:
        """
        checks if the file specified in the output path already exists
        and if yes loads it and returns a list of dictionaries.

        If not it checks if the input path points to a json file and extracts this.

        if neither it returns an empty list

        :param input_path:
        :param output_path:
        :return:
        """
        # Check if the output file exists
        # TODO Check if this path contains a extraced.kjson file  and read it
        if os.path.exists(output_path):
            return load_json_from_path(output_path)

        # Check if the input path points to a JSON file
        elif os.path.splitext(input_path)[1] == '.json':
            return load_json_from_path(input_path)

        # Return an empty list if neither condition is met
        return []

