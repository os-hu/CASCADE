import os.path
from argparse import ArgumentParser

import pandas as pd
import matplotlib.pyplot as plt


def main():
    program_name = "plot"
    description = ""
    arg = ArgumentParser(prog=program_name,
                         description=description)

    arg.add_argument('-i', '--input-path', required=True,
                     help='The path to the output.csv file')
    arg.add_argument('-o', '--output-path', required=True,
                     help='The output path in which results and temporary files will be stored, and from which the '
                          'extracted.json is read')
    arg.add_argument('-c', '--column', default='code',
                     help='The column to use to plot')
    arg.add_argument('-min', type=int, default=0,
                     help='The min length to plot')
    arg.add_argument('-max', type=int, default=10000,
                     help='The max length to plot')
    arg.add_argument('-bins', type=int, default=100,
                     help='The bins to plot')
    args = arg.parse_args()
    plot(args)


def plot(args):
    # Read the CSV file
    file_path = args.input_path
    data = pd.read_csv(file_path)

    # Specify the column name
    column_name = args.column

    # Check if the column exists in the DataFrame
    if column_name not in data.columns:
        raise ValueError(f"Column '{column_name}' not found in the CSV file.")

    data = data[data[column_name] >= args.min]
    data = data[data[column_name] <= args.max]

    print("length", len(data))

    print()

    # Plot the histogram
    plt.figure(figsize=(10, 6))
    plt.hist(data[column_name].dropna(), bins=args.bins, edgecolor='k', alpha=0.7)
    plt.title(f'Histogram of {column_name}')
    plt.xlabel(column_name)
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.savefig(os.path.join(args.output_path, f'{column_name}-histogram.pdf'))


if __name__ == '__main__':
    main()
