import requests
from bs4 import BeautifulSoup

# Specify the URL of the webpage you want to scrape
url = "https://www.qualtrics.com/support/survey-platform/actions-module/setting-up-actions/"


def run():
    # Make a request to the website
    r = requests.get(url)

    # r.content contains the HTML content you want to analyze.
    soup = BeautifulSoup(r.content, 'html.parser')

    # Now you can work with the BeautifulSoup object, 'soup'
    # print(soup.prettify())
    # Open the output file
    with open("output.txt", "w") as file:
        # Find all <p> tags
        start = False
        for p_tag in soup.find_all('p'):
            # Write the text within each <p> tag to the file
            if start:
                if "creating & managing con..." in p_tag.get_text().lower():
                    break
                file.write(p_tag.get_text())
                # file.write("\n")
            else:
                if "thank you for your feedback!" in p_tag.get_text().lower():
                    start = True
                    continue
        file.write("\n\ncompress the above as much as you can with symbols, emojis and other short hand, so that it takes as absolutely few tokens as possible, do not use line breaks, but be certain that you retain whatever is necessary for another chatbot like yourself to be able to decompress it and understand it.")


if __name__ == "__main__":
    run()
