from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from time import sleep
import os
import requests
from bs4 import BeautifulSoup
import json

# Setup
driver = webdriver.Chrome()  # or whichever browser you prefer
link_file_path = "Qlink-full-text.txt"
txt_output_file = "Qualtrics_support_full_corpus.txt"
json_output_file = "subject-link.json"


def main():
    # Navigate to the website
    # driver.get('https://www.qualtrics.com/support/survey-platform/information-survey-takers/')
    driver.get(
        'https://www.qualtrics.com/support/survey-platform/managing-your-account/creating-account-logging/')
    sleep(7)

    # Find the nav element
    nav = driver.find_element(
        By.CSS_SELECTOR, '#main > div > div > nav > ul.flex-column.flex-nowrap.nav.support-menu')
    print("nav:", nav)
    nav.screenshot('./Screenshots/nav.png')

    # Find all list items in the nav
    links_list = nav.find_elements(By.TAG_NAME, 'a')
    # print("list_itms",links_list)
    print("link count: ", len(links_list))

    # Iterate through each list item
    for link in links_list:
        print("link:", link.get_attribute("href"))
        url = link.get_attribute("href")
        # Pull the text from the page.
        text, title = get_text_from_url(url)
        # print("url:", url)
        # write_string_to_file(text,txt_output_file) # just appends the string to an output file
        # write_txt_summary(url, text) # appends url + summary to string
        # creates an inventory of the title and url
        write_json_summary(json_output_file, title, url)

    # Cleanup
    driver.quit()


def write_string_to_file(input_string, file_path):
    with open(file_path, 'a') as f:
        f.write(input_string + '\n')


def get_text_from_url(url):
    """Fetch the text from the given URL."""
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    pageContents = ''
    start = False
    pageTitle = soup.select_one(
        "#main > div > div > article > header > div.align-items-baseline.d-flex.flex-wrap.justify-content-between.pb-3.row.no-gutters > h1")
    print('title: '+pageTitle.text if pageTitle else 'no title for:{url}')
    myTitle = pageTitle.text if pageTitle else "No Title"
    for p_tag in soup.find_all('p'):
        if start:
            if "creating & managing con..." in p_tag.get_text().lower():
                break
            pageContents += p_tag.get_text().replace('Thank you for your feedback!',
                                                     '').replace("Ready to learn more about Qualtrics?", '')
        else:
            if "thank you for your feedback!" in p_tag.get_text().lower():
                start = True
                continue
    return pageContents, myTitle


def write_txt_summary(url, summary):
    """Write the summary to a text file."""
    data = load_or_create_txt_file()
    data += url+" " + \
        summary.replace("Ready to learn more about Qualtrics?", '')
    with open(txt_output_file, "w", encoding='utf-8') as txt_file:
        txt_file.write(data)


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
        # print(json_file)
        data = json.load(json_file)
    return data


def write_json_summary(file_name, subject, url):
    print(file_name, url, subject)
    data = load_or_create_json_file(file_name)
    if subject in data:
        data[subject] += ","+url
    else:
        data[subject] = url
    with open(file_name, "w") as txt_file:
        json.dump(data, txt_file)


if __name__ == "__main__":
    main()
