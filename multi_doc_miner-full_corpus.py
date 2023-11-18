import requests
from bs4 import BeautifulSoup
import openai
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from time import sleep
from qdoc_map import document_map
import html

# load environment variables and setup openai auth
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
openai.api_key = os.environ['OPENAI_KEY']

# load the data from the other file into the input variable for this file
inpts = document_map
# RAW file is for documents to summary before adding corrections.
output_file = "data/primed_created_raw-everything.json"


def run():
    with open('./data/menu_items.json', 'r') as json_file:
        documentation_links = json.load(json_file)
        for idx, item in enumerate(documentation_links):
            if idx <= 1727:
                print("skipping", idx)
                continue
            url = item['link']
            text = get_text_from_url(url)
            write_summary(item['name'], url+" "+text)
            print("idx", idx, " name:url - ", item['name'], " : ", url)
            # sleep(1)


def write_summary(subject, summary):
    file_name = output_file
    data = load_or_create_json_file()
    clean_summary = html.unescape(summary)
    if subject in data:
        data[subject] += clean_summary+" "
    else:
        data[subject] = clean_summary
    with open(file_name, "w", encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False)


def get_text_from_url(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    accum = ''
    start = False
    for p_tag in soup.find_all('p'):
        if start:
            if "creating & managing con..." in p_tag.get_text().lower():
                break
            text = p_tag.get_text()
            if text:
                text = text.strip()
                accum += text + " "
        else:
            if "thank you for your feedback!" in p_tag.get_text().lower():
                start = True
                continue
    return accum.replace("Thank you for your feedback!", '').replace("/2\n                    Ready to learn more about Qualtrics?", "").strip()


def load_or_create_json_file():
    file_name = output_file
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding='utf-8') as json_file:
            json.dump({}, json_file)
    # Read the file data
    with open(file_name, "r", encoding='utf-8') as json_file:
        data = json.load(json_file)

    return data


if __name__ == "__main__":
    run()
