import unittest
from utils.Utils import load_json_from_path
from utils.Utils import save_dicts_list_to_json


class test_Utils(unittest.TestCase):
    """
    for this the follwoing files and folders have to exist:
    TODO fill this
    """

    def test_load_json_from_path(self):
        test_list_dict = load_json_from_path("./test_resources/test_load.json")
        self.assertEqual(test_list_dict, [{"id": 1,"name" : "test"},{"id" : 2,"name2" : "test2"}])
        self.assertIsInstance(test_list_dict[0]["id"] , int)


    def test_save_dicts_list_to_json_errors(self):
        test_list = [{"id": 1,"name" : "test"},{"id" : 2,"name2" : "test2"}]

        with self.assertRaises(ValueError):
            file_path = "./test_resources/not_existent_folder/"
            save_dicts_list_to_json(test_list, file_path)

        # override not allowed
        with self.assertRaises(ValueError):
            file_path = "./test_resources/test_load.json"
            save_dicts_list_to_json(test_list, file_path)

    def test_save_dicts_list_to_json(self):
        test_list = [{"id": 1, "name": "test"}, {"id": 2, "name2": "test2"}]

        file_path = "./test_resources/test_load.json"
        save_dicts_list_to_json(test_list, file_path, override=True)

        #file_path = "./test_resources/test_load2.json"
        #save_dicts_list_to_json(test_list, file_path, override=False)


    def test_save_dicts_list_to_json_create(self):
        test_list = [{"id": 1, "name": "test"}, {"id": 2, "name2": "test2"}]

        # TODO chekc if folder exxitsts is false

        #file_path = "./test_resources/temp/new_folder/test_load2.json"
        #save_dicts_list_to_json(test_list, file_path, create_folder=True)

        # TODO chekc if folder exxitsts is True    and the ndleete it again