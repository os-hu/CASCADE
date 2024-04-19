import json
import os
from typing import List, Dict, Any

def load_json_from_path(file_path):
    """
    :return:
    """
    # TODO maybe use the functionaility from Human_Eval_basic_Extraction
    # TODO add error handling the filed does not exist or is not a file?
    with open(file_path, 'r') as file:
        data = json.load(file)

    return data


def save_dicts_list_to_json(data: List[Dict[str, Any]], file_path: str, create_folder=False, override=False):
    """
    this saves a list of dictionaries to a json file in the json list format [{},{},{},...]
    :param data: the list of dictionaries that should be saved
    :param file_path: needs to be a path ending with a file name.
    :param create_folder:  if this is True than the specified folder is created if it does not already exist.
    :param override:  a boolean determining whether the specified file can be overridden if it already exists
    """
    # check if file exists
    if os.path.exists(file_path) and os.path.isfile(file_path):
        if override:
            #print("override specified file")
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

        else:
            # error   # TODO handle error? ask for other name?    this way is not good  everything will be lost.
            # TODO save to a temp folder?
            raise ValueError("file already exists and 'override' is set to False")

    # if file does not exist ...
    else:
        # ... check if the specified directory exists
        if os.path.exists(os.path.dirname(file_path)):
            #print("create file in specified folder")
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

        # if not, create it if allowed
        else:
            if create_folder:
                # print(f"create specified file {file_path} and folder {os.path.dirname(file_path)}")
                os.makedirs( os.path.dirname(file_path))
                with open(file_path, 'w') as file:
                    json.dump(data, file, indent=4)

            else:
                raise ValueError(f"specified folder {os.path.dirname(file_path)} does not exist and 'create_folder' is set to False")
