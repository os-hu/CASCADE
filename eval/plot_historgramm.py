import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file
file_path = './output.csv'
data = pd.read_csv(file_path)

# Specify the column name
column_name = 'code' #'doc'

# Check if the column exists in the DataFrame
if column_name not in data.columns:
    raise ValueError(f"Column '{column_name}' not found in the CSV file.")



#data = data[data[column_name] >= 10]
#data = data[data[column_name] <= 2000]

print(data[column_name].max())
print()

print(data["id"][data[column_name].argmax()])

# Plot the histogram
plt.figure(figsize=(10, 6))
plt.hist(data[column_name].dropna(), bins=100, edgecolor='k', alpha=0.7)
plt.title(f'Histogram of {column_name}')
plt.xlabel(column_name)
plt.ylabel('Frequency')
plt.grid(True)
#plt.show()