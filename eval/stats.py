import os.path
import sys
from collections import defaultdict, Counter

import tiktoken

import csv

from cascade.PipelineFactory import PipelineFactory
from cascade.extraction.JsonExtraction import JsonExtraction
from cascade.filters.Filter import Filter
from cascade.filters.KeyExistsFilterFunction import KeyExistsFilterFunction
from cascade.filters.NoTestsFilterFunction import NoTestsFilterFunction
from cascade.filters.ContainsFilterFunction import ContainsFilterFunction
from cascade.filters.CheckLengthFilterFunction import CheckLengthFilterFunction

from argparse import ArgumentParser


def main():
    program_name = "stats"
    description = ""
    arg = ArgumentParser(prog=program_name,
                                description=description)

    arg.add_argument('-i', '--input-path',
                     help='The input path which will be used for generating stats')
    arg.add_argument('-o', '--output-path', required=True,
                     help='The output path in which results and temporary files will be stored, and from which the extracted.json is read')
    arg.add_argument('-s', '--setup-file',
                     help='The path to the setup file defining the pipeline to use the extraction and filters from')
    arg.add_argument('--skip-classes-skipped',
                     help='Skip printing the top classes skipped due to step size', action='store_true')
    arg.add_argument('--skip-top-5',
                     help='Skip printing the top 5 stats', action='store_true')
    arg.add_argument('--skip-csv',
                     help='Skip writing the stats to csv', action='store_true')
    arg.add_argument('--skip-length',
                     help='Skip printing the amount of functions in the dataset', action='store_true')
    arg.add_argument('--encoder', default='gpt-3.5-turbo-instruct',
                     help='The encoder to use for string lengths (\'text\' for basic string length)')
    args = arg.parse_args()

    if bool(args.input_path) != bool(args.setup_file):
        args.error("If -i or -s is set, the other also has to be set!")
    stats(args)


class _Text:
    def encode(self, string):
        return list(string)


def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def process_entry(entry, enc):
    flattened = flatten_dict(entry)
    result = {}
    for key, value in flattened.items():
        # Check if the value is a list or similar iterable, otherwise treat as a single item

        if key == "id":
            result[key] = value

        elif hasattr(value, '__len__'):  # and not isinstance(value, str):
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


def write_length_stats(data, out_path, enc):
    all_keys = set()
    processed_data = []

    # Process each entry, flatten and calculate lengths
    for entry in data:
        processed_entry = process_entry(entry, enc)
        processed_data.append(processed_entry)
        all_keys.update(processed_entry.keys())

    # Ensure each dictionary has all keys
    for entry in processed_data:
        for key in all_keys:
            entry.setdefault(key, "N")  # N for non-existent keys

    # Write to CSV
    with open(os.path.join(out_path, "output.csv"), "w", newline="") as csvfile:
        fieldnames = list(all_keys)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for entry in processed_data:
            writer.writerow(entry)


def print_histograms(dicts, enc, top_n=5):
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
            print(f'  Value: {value}, Count: {count}, Length: {len(enc.encode(value))}')
        print()


def stats(args):
    if args.encoder == 'text':
        enc = _Text()
    else:
        try:
            enc = tiktoken.encoding_for_model(args.encoder)
        except:
            sys.stderr.write(f"Could not load encoder {args.encoder}!")
            sys.exit(-1)

    in_path = args.input_path
    out_path = args.output_path

    if args.setup_file:
        try:
            pipeline = PipelineFactory().build(args.setup_file)
            data = pipeline.extraction.extract(in_path, out_path)
            data = pipeline.filter.filter_all(data)
            step_size = 1
            if hasattr(pipeline.analysis, 'step_size'):
                step_size = pipeline.analysis.step_size
        except:
            sys.stderr.write(f"Could not use pipeline {args.setup_file} on path {args.input_path} to extract "
                             f"to {args.output_path}!")
            sys.exit(-1)
    else:
        extr = JsonExtraction()
        data = extr.extract(in_path, out_path)

        if data[0]["language"] == "Java":
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
                ]
            )
            data = filter_.filter_all(data)
        step_size = 1

    if not args.skip_length:
        print(len(data))
    backup = data
    data = data[::step_size]
    if not args.skip_length:
        print(len(data))

    if not args.skip_classes_skipped:
        unique_classes = set()
        for d in data:
            unique_classes.add(d["package"] + "." + d["parent"]["name"])

        print("unique classes:" , len(unique_classes))

        for d in backup:
            unique_classes.add(d["package"] + "." + d["parent"]["name"])

        print("from original classes:" , len(unique_classes))

    if not args.skip_csv:
        write_length_stats(data, out_path, enc)

    if not args.skip_top_5:
        print_histograms(data, enc)


if __name__ == '__main__':
    main()