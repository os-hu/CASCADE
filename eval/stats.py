import os.path

from src.extraction.JavaExtraction import JavaExtraction
from src.filters.Filter import Filter
from src.filters.NoTestsFilterFunction import NoTestsFilterFunction
from src.filters.ContainsFilterFunction import ContainsFilterFunction
from src.generation.test.GPT35JavaTestGenerator import GPT35JavaTestGenerator

in_path = "/home/kiecketo/repos/commons-text"
out_path = os.path.dirname(__file__)


extr = JavaExtraction()
data = extr.extract(in_path, out_path)

print(len(data))

filter_ = Filter(
    [NoTestsFilterFunction(),
     ContainsFilterFunction("signature.modifier", "public"),
     ContainsFilterFunction("doc", "@inheritDoc", invert=True)
     ]
)

filtered_data = filter_.filter_all(data, out_path)

print(len(filtered_data))


for d in filtered_data[120:124]:
    test_prompt = GPT35JavaTestGenerator("", dummy=True).build_prompt(d)
    print(test_prompt)
    print("--------------------------")