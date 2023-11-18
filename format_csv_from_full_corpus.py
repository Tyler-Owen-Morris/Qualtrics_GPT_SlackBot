import pandas as pd
import json
import csv

# The name of the input JSON file
json_file_name = './data/primed_created_raw-everything.json'
# The name of the output CSV file
csv_file_name = './data/full_Qdocs_corpus.csv'


def run():

    # Load the JSON file into a Python dictionary
    with open(json_file_name, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # Process the data to remove newline characters from 'content'
    processed_data = {k: v.replace('\n', ' ').replace(
        '\r', ' ').replace(',', '') for k, v in data.items()}

    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(list(processed_data.items()),
                      columns=['subject', 'content'])

    # Add the dummy 'bot_id' and 'tokens' columns with empty string as placeholder values
    df['bot_id'] = '4'
    df['tokens'] = '0'

    # Write the DataFrame to a CSV file, handling the Unicode encoding error by using utf-8 encoding
    # and ensuring non-numeric fields are quoted properly
    df.to_csv(csv_file_name, index=False, encoding='utf-8',
              quotechar='"', quoting=csv.QUOTE_NONNUMERIC, escapechar='\\')

    print(f'Data has been written to {csv_file_name}')


if __name__ == "__main__":
    run()
