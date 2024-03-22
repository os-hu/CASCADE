import unittest
from src.Utils import load_json_from_path

class test_Utils(unittest.TestCase):

    def test_load_json_from_path(self):
        test_list_dict = load_json_from_path("./test_resources/test_load.json")
        self.assertEqual(test_list_dict, [{"id": 1,"name" : "test"},{"id" : 2,"name2" : "test2"}])
        self.assertIsInstance(test_list_dict[0]["id"] , int)
