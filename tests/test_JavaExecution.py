import unittest
from src.analysis.executor.JavaExecutor import JavaExecutor

context = {
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
    "new_code": "{\n    System.out.println(\"I was executed\");\n}",
    "code_file_path": "src/TestClass.java",
    "called_functions": [],
    "tests": "import java.util.List;\n\n/**\n * A class to test the extraction\n */\npublic class TestClassTest {\n\n    volatile private int a;\n\n    /**\n     *        The very important doStuff function that as it says does stuff\n     */\n    public void testDoStuff(int x, float test) {\n        return;\n    }\n}\n",
    "new_tests": "import java.util.List;\nimport TestClass;\nimport org.junit.jupiter.api.Test;\n\n/**\n * A class to test the extraction\n */\npublic class TestClassTest {\n\n    volatile private int a;\n\n    /**\n     *        The very important doStuff function that as it says does stuff\n     */\n    @Test\n    public void testDoStuff(int x, float test) {\n        new TestClass().doStuff();\n        return;\n    }\n}\n",
    "test_imports": "[import java.util.List;\n]",
    "test_file_path": "test/TestClassTest.java"
}


class test_JavaExecution(unittest.TestCase):
    def test_source_execute(self):
        executor = JavaExecutor(debug=True)
        executor.execute("new_code", "new_tests", context)
        
