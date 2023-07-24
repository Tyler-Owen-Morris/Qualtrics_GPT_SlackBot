import os
import requests
import openai
import json
from time import sleep
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv
from qdoc_map import document_map
from transformers import GPT2Tokenizer

# load environment variables and setup openai auth
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
openai.api_key = os.getenv('OPENAI_KEY')

# setup tokenizer for counting tokens
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')

# load the data from the other file into the input variable for this file
# RAW file is for documents to summary before adding corrections.
txt_output_file = "data/primer_data_summarized_full.txt"
json_output_file = "data/primer_data_summarized_full.json"


def run():
    inpts = load_or_create_json_file("mining/subject-link.json")
    """Main function to run the script."""
    for subject, url in inpts.items():
        text = get_text_from_url(url)
        print("url:", url)
        print("subject:",subject)
        # write_txt_summary(url, text) # just writes the text to
        gpt_summary = get_summary_from_text(text)
        write_gpt_summary(subject, url+" "+gpt_summary)
        sleep(5)



def write_txt_summary(url, summary):
    """Write the summary to a text file."""
    data = load_or_create_txt_file()
    data += "\n"+url+" : " + \
        summary.replace("Ready to learn more about Qualtrics?", '')
    with open(txt_output_file, "w", encoding='utf-8') as txt_file:
        txt_file.write(data)

def write_gpt_summary(subject, summary):
    data = load_or_create_json_file(file_name=json_output_file)
    if subject in data:
        data[subject] += summary+" "
    else:
        data[subject] = summary
    with open(json_output_file, "w") as json_file:
        json.dump(data, json_file)


def get_summary_from_text(text):
    try:
        full_msg = create_gpt_message(text)
        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=full_msg
        )
        resp = completion.choices[0].message.content
        print("summary:\n", resp, "\n*********")
        return resp
    except Exception as e:
        print("sleeping before retry",e)
        sleep(30)
        print("retrying:",text)
        return get_summary_from_text(text)

def get_text_from_url(url):
    """Fetch the text from the given URL."""
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    pageContents = ''
    start = False
    for p_tag in soup.find_all('p'):
        if start:
            if "creating & managing con..." in p_tag.get_text().lower():
                break
            pageContents += p_tag.get_text().replace('Thank you for your feedback!','').replace("Ready to learn more about Qualtrics?",'')
        else:
            if "thank you for your feedback!" in p_tag.get_text().lower():
                start = True
                continue
    return pageContents

def load_or_create_txt_file():
    """Load the text file, or create it if it doesn't exist."""
    if not os.path.exists(txt_output_file):
        os.makedirs(os.path.dirname(txt_output_file), exist_ok=True)
    with open(txt_output_file, "r", encoding='utf-8') as txt_file:
        data = txt_file.read()
    return data

def load_or_create_json_file(file_name):
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, "w") as json_file:
            json.dump({}, json_file)
    # Read the file data
    with open(file_name, "r") as json_file:
        data = json.load(json_file)

    return data

def create_gpt_message(text):
    system_message = "you are a summary assistant. You will take in a large block of text from Qualtrics documentation and compress it into the fewest tokens possible while allowing a large language model to understand the content. do not remove important technical details. Retain comprehension of detailed instructions. say OK if you understand."
    user_message = text
    while count_string_tokens(system_message) + count_string_tokens(user_message) > 4096:
        str_remove_count = (count_string_tokens(system_message) + count_string_tokens(user_message))- 4096
        if str_remove_count < 10:
            str_remove_count = 10
        user_message = user_message[:-str_remove_count]
        print("over token count:",count_string_tokens(system_message) + count_string_tokens(user_message),"\nRemoving:",str_remove_count)
    msg = [{'role': 'system', 'content': system_message}, {
            'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': user_message}]
    return msg
    
def count_conversation_tokens(conversation):
    total_tokens = 0
    # print(conversation)
    for message in conversation:
        # print(message)
        # print(type(message))
        tokens = tokenizer.tokenize(message['content'])
        total_tokens += len(tokens) + 3
    return total_tokens

def count_string_tokens(string):
    tokens = tokenizer.tokenize(string)
    return len(tokens) + 3

if __name__ == "__main__":
    run()
