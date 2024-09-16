import re
import unittest

from cascade.filters.Filter import Filter
from cascade.filters.NoTestsFilterFunction import NoTestsFilterFunction
from cascade.generation.code.GPT4JavaCodeGenerator import GPT4JavaCodeGenerator
from cascade.generation.test.GPT4JavaTestGenerator import GPT4JavaTestGenerator
from cascade.utils.Utils import load_json_from_path

class test_GPT4Java(unittest.TestCase):


    def test_prompt(self):
        generator = GPT4JavaTestGenerator()

        data = load_json_from_path("./resources/extracted.json")

        _filter = Filter([NoTestsFilterFunction()])

        data = _filter.filter_all(data)
        context = data[1]

        generator.is_three = True

        prompt = generator.build_tests(context)
        #print(prompt[1]["content"])
        print(prompt)

        #nc , response = generator.generate(context, "./resources", "")
        #print(nc)
        #print(context['doc'])
        #print("-------")
        #print(context['code'])
        #print("-------")
        #print(response)

    def test_generate(self):
        new_code = "The body of the `getTrimmerMatcher` function would depend on how the `StrTokenizer` class is implemented. However, assuming that there is a private `StrMatcher` field named `trimmerMatcher` that holds the current trimmer matcher, the function could be implemented as follows:\n\n```java\npublic StrMatcher getTrimmerMatcher() {\n    return this.trimmerMatcher; { test class} test array[]]\n}\n  next function```\n\nThis function simply returns the current trimmer matcher. If the `trimmerMatcher` field does not exist or is named differently, you would need to replace `trimmerMatcher` with the correct field name."


        pattern = r"```java(.*?)```"
        code_blocks = re.findall(pattern, new_code, flags=re.DOTALL)
        if code_blocks == []:
            print("No explicit code block found in response")
        else:
            # now we have to cut out the actual function inside of the code block
            new_code = code_blocks[0].strip()
            pattern = r"\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}"   # should match only outermost brackets

            code_blocks = re.findall(pattern, new_code, flags=re.DOTALL)

            if code_blocks == []:
                print("No explicit code block found in response")
            else:
                new_code = code_blocks[0]


        print(new_code)








if __name__ == '__main__':
    unittest.main()
