import pandas as pd
import json

input_data_file = "data/primed_created_raw.json"
corrections_file = "data/corrections.csv"
output_file = "data/primed_created_merged.json"


def merge_corrections(input_file=input_data_file, corrections_file=corrections_file, output_file=output_file):
    # read in the input files
    in_data = load_json_file(input_file)
    # print("data_type:", type(in_data))
    corrections_df = pd.read_csv(corrections_file, na_filter=False)
    for idx, row in corrections_df.iterrows():
        # print("row:", row)
        subject = row['subject']
        content = row['correction']
        # print("subject:", subject, "|content:", content)
        if subject in list(in_data.keys()):
            print("found:", in_data[subject])
            in_data[subject] += (" "+content)
        else:
            print("Did not find:", subject)
            in_data[subject] = content
    write_to_output(in_data, output_file)
    pass


def write_to_output(data, write_file):
    with open(write_file, "w") as f:
        json.dump(data, f)


def load_json_file(fname):
    # Read the file data
    with open(fname, "r") as json_file:
        data = json.load(json_file)
    return data


if __name__ == "__main__":
    merge_corrections()
