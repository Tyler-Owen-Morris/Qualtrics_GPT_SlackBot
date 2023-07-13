import os
import requests
import openai
from time import sleep
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv
from qdoc_map import document_map

# load environment variables and setup openai auth
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
openai.api_key = os.getenv('OPENAI_KEY')

# load the data from the other file into the input variable for this file
inpts = document_map
# RAW file is for documents to summary before adding corrections.
txt_output_file = "data/large-text-loader2.txt"


def run():
    """Main function to run the script."""
    for _, url in inpts:
        text = get_text_from_url(url)
        print("url:", url)
        write_txt_summary(url, text)
        sleep(3)


def write_txt_summary(url, summary):
    """Write the summary to a text file."""
    data = load_or_create_txt_file()
    data += "\n"+url+" : " + \
        summary.replace("Ready to learn more about Qualtrics?", '')
    with open(txt_output_file, "w", encoding='utf-8') as txt_file:
        txt_file.write(data)


def get_text_from_url(url):
    """Fetch the text from the given URL."""
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    accum = ''
    start = False
    for p_tag in soup.find_all('p'):
        if start:
            if "creating & managing con..." in p_tag.get_text().lower():
                break
            accum += p_tag.get_text()
        else:
            if "thank you for your feedback!" in p_tag.get_text().lower():
                start = True
                continue
    return accum


def load_or_create_txt_file():
    """Load the text file, or create it if it doesn't exist."""
    if not os.path.exists(txt_output_file):
        os.makedirs(os.path.dirname(txt_output_file), exist_ok=True)
    with open(txt_output_file, "r", encoding='utf-8') as txt_file:
        data = txt_file.read()
    return data


if __name__ == "__main__":
    run()
