import os.path
from collections import defaultdict, Counter

import tiktoken

import csv


from src.extraction.JavaExtraction import JavaExtraction
from src.filters.Filter import Filter
from src.filters.KeyExistsFilterFunction import KeyExistsFilterFunction
from src.filters.NoTestsFilterFunction import NoTestsFilterFunction
from src.filters.ContainsFilterFunction import ContainsFilterFunction
from src.generation.code.GPT35JavaCodeGenerator import GPT35JavaCodeGenerator
from src.generation.test.GPT35JavaTestGenerator import GPT35JavaTestGenerator
from src.filters.CheckLengthFilterFunction import CheckLengthFilterFunction



enc = tiktoken.encoding_for_model("gpt-3.5-turbo-instruct")


in_path = "/home/kiecketo/repos/jfreechart"
out_path = "/home/kiecketo/PycharmProjects/CASCADE/eval/jfreechart"


extr = JavaExtraction()
data = extr.extract(in_path, out_path)

filter_ = Filter(
    [
        CheckLengthFilterFunction("doc", ">", 12, encoder="gpt-3.5-turbo-instruct"),
        ContainsFilterFunction("doc", "@inheritDoc", invert=True),
        ContainsFilterFunction("signature.modifier", "public"),
        ContainsFilterFunction("signature.modifier", "static", invert=True),
        NoTestsFilterFunction(),
        KeyExistsFilterFunction("code"),
        CheckLengthFilterFunction(key="code", op=">", val=2, encoder="gpt-3.5-turbo-instruct"),
        CheckLengthFilterFunction(key="code", op="<", val=200, encoder="gpt-3.5-turbo-instruct"),
        #ContainsFilterFunction("signature.name", "Draw"),
#        ContainsFilterFunction("signature.name", "get", invert=True),
#        ContainsFilterFunction("signature.name", "set", invert=True),
    ]
)

step_size = 1

print(len(data))
data = filter_.filter_all(data)
backup = data
data = data[::step_size]
print(len(data))

unique_classes = set()
for d in data:
    unique_classes.add(d["package"] + "." + d["parent"]["name"])

print("unique classes:" , len(unique_classes))

for d in backup:
    unique_classes.add(d["package"] + "." + d["parent"]["name"])

print("from original classes:" , len(unique_classes))



def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def process_entry(entry):
    flattened = flatten_dict(entry)
    result = {}
    for key, value in flattened.items():
        # Check if the value is a list or similar iterable, otherwise treat as a single item

        if key == "id":
            result[key] = value


        elif hasattr(value, '__len__'): # and not isinstance(value, str):
            if isinstance(value, str):
                # Strings are encoded and the returned number is the numebr of tokens
                result[key] = len(enc.encode(value))
                if entry["id"] == 1050:
                    print(len(enc.encode(value)), key, value, enc.encode(value))
            else:
                result[key] = len(value)
        elif value is None:
            result[key] = 'None'
        else:
            result[key] = 1  # Default length for single items
    return result


def write_length_stats(data):
    all_keys = set()
    processed_data = []

    # Process each entry, flatten and calculate lengths
    for entry in data:
        processed_entry = process_entry(entry)
        processed_data.append(processed_entry)
        all_keys.update(processed_entry.keys())

    # Ensure each dictionary has all keys
    for entry in processed_data:
        for key in all_keys:
            entry.setdefault(key, "N")  # N for non-existent keys

    # Write to CSV
    with open(os.path.join(out_path, "output.csv")  , "w", newline="") as csvfile:
        fieldnames = list(all_keys)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for entry in processed_data:
            writer.writerow(entry)


def print_histograms(dicts, top_n=5):
    # Step 1: Flatten all dictionaries
    flattened_dicts = [flatten_dict(d) for d in dicts]

    # Step 2: Collect all values for each key
    key_value_counts = defaultdict(Counter)
    for flat_dict in flattened_dicts:
        for key, value in flat_dict.items():
            key_value_counts[key][str(value)] += 1

    # Step 3: Print the histogram of the most common values for each key
    for key, counter in key_value_counts.items():
        print(f'Key: {key}')
        most_common = counter.most_common(top_n)
        for value, count in most_common:
            print(f'  Value: {value}, Count: {count}, Length: {len(value)}')
        print()



write_length_stats(data)

#print_histograms(data)