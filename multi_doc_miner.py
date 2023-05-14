import requests
from bs4 import BeautifulSoup
import openai
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from time import sleep
from qdoc_map_adhoc import document_map

# load environment variables and setup openai auth
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
openai.api_key = os.environ['OPENAI_KEY']

# load the data from the other file into the input variable for this file
inpts = document_map
output_file = "data/primed_created-1.json"


def run():
    for tpl in inpts:
        # get the HTML
        subject = tpl[0]
        url = tpl[1]
        text = get_text_from_url(url)
        # make the summary
        summary = get_summary_from_text(text)
        # Write the summary to the json file
        write_summary(subject, url+" "+summary)
        sleep(3)


def write_summary(subject, summary):
    file_name = output_file
    data = load_or_create_json_file()
    if subject in data:
        data[subject] += summary+" "
    else:
        data[subject] = summary
    with open(file_name, "w") as json_file:
        json.dump(data, json_file)


def get_summary_from_text(text):
    try:
        full_msg = [{'role': 'system', 'content': 'you are a summary assistant. You will take in a large block of text from Qualtrics documentation and compress it into the fewest tokens possible while allowing a large language model to understand the content. do not remove important technical details. Retain comprehension of detailed instructions. say OK if you understand.'}, {
            'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': text}]
        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=full_msg
        )
        resp = completion.choices[0].message.content
        print("summary:", resp)
        return resp
    except Exception as e:
        sleep(30)
        return get_summary_from_text(text)


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
    accum += "\n\ncompress the above as much as you can with symbols, emojis and other short hand, so that it takes as absolutely few tokens as possible, do not use line breaks, but be certain that you retain whatever is necessary for another chatbot like yourself to be able to decompress it and understand it."
    return accum


def load_or_create_json_file():
    file_name = output_file
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
