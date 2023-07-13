import requests
from bs4 import BeautifulSoup
import openai
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from time import sleep
from qdoc_map import document_map

# load environment variables and setup openai auth
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
openai.api_key = os.environ['OPENAI_KEY']

# load the data from the other file into the input variable for this file
inpts = document_map
# RAW file is for documents to summary before adding corrections.
txt_output_file = "data/large-text-loader1.txt"
json_output_file = "data/primed_created1.json"


def run():
    for tpl in inpts:
        # get the HTML
        subject = tpl[0]
        url = tpl[1]
        text = get_text_from_url(url)
        # print("text:", text)
        print("url:", url)
        # Write the summary to the file
        write_txt_summary(url, text)
        sleep(3)


def write_txt_summary(url, summary):
    file_name = txt_output_file
    data = load_or_create_txt_file()
    # if subject in data:
    #     data+= summary
    # else:
    #     data = summary
    data += "\n"+url+" : "+summary
    with open(file_name, "w") as txt_file:
        json.dump(data, txt_file)


def write_json_summary(subject, summary):
    file_name = json_output_file
    data = load_or_create_json_file()
    if subject in data:
        data[subject] += summary+" "
    else:
        data[subject] = summary
    with open(file_name, "w") as txt_file:
        json.dump(data, txt_file)


def get_text_from_url(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    accum = ''
    start = False
    for p_tag in soup.find_all('p'):
        if start:
            if "creating & managing con..." in p_tag.get_text().lower():
                break
            # file.write(p_tag.get_text())
            # file.write("\n")
            accum += p_tag.get_text()
        else:
            if "thank you for your feedback!" in p_tag.get_text().lower():
                start = True
                continue
    return accum


def load_or_create_txt_file():
    file_name = txt_output_file
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        try:
            with open(file_name, "w") as txt_file:
                txt_file.write("")
        except PermissionError:
            print(f"Permission denied: Unable to write to {file_name}")
            return None

    # Read the file data
    try:
        with open(file_name, "r") as txt_file:
            data = txt_file.read()
    except PermissionError:
        print(f"Permission denied: Unable to read from {file_name}")
        return None

    return data


def load_or_create_json_file():
    file_name = json_output_file
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, "w") as json_file:
            json.dump({}, json_file)
    # Read the file data
    with open(file_name, "r") as json_file:
        data = json.load(json_file)

    return data


if __name__ == "__main__":
    run()
