import json

def load_json_from_path(file_path):
    """
    :return:
    """
    with open(file_path, 'r') as file:
        data = json.load(file)

    return data
