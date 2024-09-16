import unittest

from cascade.filters.Filter import Filter
from cascade.filters.NoTestsFilterFunction import NoTestsFilterFunction
from cascade.generation.test.GPT4JavaTestGenerator import GPT4JavaTestGenerator
from cascade.utils.Utils import load_json_from_path

class test_GPT4Java(unittest.TestCase):


    def test_prompt(self):
        generator = GPT4JavaTestGenerator()
        data = load_json_from_path("./resources/extracted.json")

        _filter = Filter([NoTestsFilterFunction()])

        data = _filter.filter_all(data)
        context = data[1]

        nt , response = generator.generate(context, "./resources", "")
        print(nt)
        print("-------")
        print(response)
        #self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
