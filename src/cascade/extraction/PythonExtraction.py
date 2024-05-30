from cascade.extraction.Extraction import Extraction


class PythonExtraction(Extraction):
    """
    An implementation of the abstract "Extraction" class.
    This is designed to extract all functions, corresponding tests, docstrings and context from a given python Project
    """
    def __init__(self):
        super().__init__()

    def extract(self, input_path, output_path, print_mode=False) -> dict:
        """

        :param input_path:
        :param output_path:
        :param print_mode:
        :return:
        """

        result = {
            "root_path": "",
            "doc": "",
            "signature": {
                "name": "",
                "returns": "",
                "params": "",
                # "annotations": "",
                # "generics" : ""
            },
            "language": "python",
            "parent": {
                "name": "",
                "doc": "",
                "imports": [],
                "other_methods": [],
                "variables": [],
                # "generics" : ""
            },
            "code": "",
            # "new_code" : "",
            "code_file_path": "",    # THIS IS IMPORTANT
            "called_functions": [],
            "tests": "",
                # the tests shoudl be in a format such that they can be put at the verry top of the project and be able to import the desired function.
            "test_imports": [],
            "test_file_path": "",
            "testrunner": "unnittest",
        }

        return {}
