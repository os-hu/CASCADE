import unittest
import os
from src.extraction.JavaExtraction import JavaExtraction

class test_JavaExtraction(unittest.TestCase):

    def test_source_extract(self):
        extract = JavaExtraction()
        path = os.path.join(".", "resources", "java")
        extracted = extract.extract(os.path.join(path, "in"), os.path.join(path, "out"))
        expected = [
            {
                "root_path": "./resources/java/in",
                "doc": "/**\n *        The very important doStuff function that as it says does stuff\n */\n",
                "signature": {
                    "name": "testDoStuff",
                    "returns": "void",
                    "params": [
                        "int x",
                        "float test"
                    ],
                    "modifier": [
                        "public "
                    ],
                    "annotations": [],
                    "generics": []
                },
                "language": "Java",
                "parent": {
                    "name": "TestClassTest",
                    "doc": "/**\n * A class to test the extraction\n */\n",
                    "imports": [
                        "import java.util.List;\n"
                    ],
                    "other_methods": [],
                    "variables": [
                        "volatile private int a;"
                    ],
                    "generics": []
                },
                "code": "{\n    return;\n}",
                "code_file_path": "test/TestClassTest.java",
                "called_functions": []
            },
            {
                "root_path": "./resources/java/in",
                "doc": "/**\n *        The very important doStuff function that as it says does stuff\n */\n",
                "signature": {
                    "name": "doStuff",
                    "returns": "void",
                    "params": [
                        "int x",
                        "float test"
                    ],
                    "modifier": [
                        "public "
                    ],
                    "annotations": [],
                    "generics": []
                },
                "language": "Java",
                "parent": {
                    "name": "TestClass",
                    "doc": "/**\n * A class to test the extraction\n */\n",
                    "imports": [
                        "import java.util.List;\n"
                    ],
                    "other_methods": [],
                    "variables": [
                        "volatile private int a;"
                    ],
                    "generics": []
                },
                "code": "{\n    return;\n}",
                "code_file_path": "src/TestClass.java",
                "called_functions": [],
                "tests": "import java.util.List;\n\n/**\n * A class to test the extraction\n */\npublic class TestClassTest {\n\n    volatile private int a;\n\n    /**\n     *        The very important doStuff function that as it says does stuff\n     */\n    public void testDoStuff(int x, float test) {\n        return;\n    }\n}\n",
                "test_imports": "[import java.util.List;\n]",
                "test_file_path": "test/TestClassTest.java"
            }
        ]
        self.maxDiff = None
        self.assertCountEqual(extracted, expected)

        os.remove(os.path.join(path, "out", "extracted.json"))

    def test_json_extract(self):
        extract = JavaExtraction()
        path = os.path.abspath(os.path.join(".", "resources", "java"))
        extracted = extract.extract(os.path.join(path, "broken"), os.path.join(path, "json"))
        expected = [{'doc': '/**\n *        The very important doStuff function that as it says does stuff\n */\n',
                     'signature': {'name': 'testDoStuff', 'returns': 'void', 'params': '(int x, float test)',
                                   'modifier': 'public',
                                   'annotations': '[]', 'generics': '[]'}, 'language': 'Java',
                     'parent': {'name': 'TestClassTest', 'doc': '/**\n * A class to test the extraction\n */\n',
                                'imports': '[import java.util.List;\n]', 'other_methods': '[]',
                                'variables': '[volatile private int a;]', 'generics': '[]'}, 'code': '{\n    return;\n}',
                     'code_file_path': '/home/jan/work/CASCADE/tests/resources/java/in/test/TestClassTest.java',
                     'called_functions': '[]'},
                    {'doc': '/**\n *        The very important doStuff function that as it says does stuff\n */\n',
                     'signature': {'name': 'doStuff', 'returns': 'void', 'params': '(int x, float test)', 'modifier': 'public',
                                   'annotations': '[]', 'generics': '[]'}, 'language': 'Java',
                     'parent': {'name': 'TestClass', 'doc': '/**\n * A class to test the extraction\n */\n',
                                'imports': '[import java.util.List;\n]', 'other_methods': '[]',
                                'variables': '[volatile private int a;]', 'generics': '[]'}, 'code': '{\n    return;\n}',
                     'code_file_path': '/home/jan/work/CASCADE/tests/resources/java/in/src/TestClass.java',
                     'tests': 'import java.util.List;\n\n/**\n * A class to test the extraction\n */\npublic class TestClassTest {\n\n    volatile private int a;\n\n    /**\n     *        The very important doStuff function that as it says does stuff\n     */\n    public void testDoStuff(int x, float test) {\n        return;\n    }\n}\n',
                     'test_imports': '[import java.util.List;\n]',
                     'test_file_path': '/home/jan/work/CASCADE/tests/resources/java/in/test/TestClassTest.java',
                     'called_functions': '[]'}]
        self.assertTrue(all([e in extracted for e in expected]) and all([e in expected for e in extracted]))
