import requests
from bs4 import BeautifulSoup
import json

# Your target URL
url = 'https://www.qualtrics.com/support/vocalize/getting-started-vocalize/dashboard-overview/'


def run():
    count = 0
    response = requests.get(url)
    menu_items = []
    # Ensure the request was successful with status code 200
    if response.status_code == 200:
        # Parse the content of the request with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the nav element with id 'menu-location'
        nav = soup.find('nav', id='menu-location')

        # Check if the nav element was found before proceeding
        if nav:
            # Extract all 'a' tags within the nav element
            a_tags = nav.find_all('a')

            # Iterate over each 'a' tag and print its 'href' attribute
            for a_tag in a_tags:
                if 'href' in a_tag.attrs:
                    name = a_tag.get_text(strip=True)
                    link = a_tag.attrs['href']
                    print(name, " : ", link)
                    menu_items.append({'name': name, 'link': link})
                    count += 1
        else:
            print('The nav element with id "menu-location" was not found on the page.')
    else:
        print(
            f'Failed to retrieve webpage, status code: {response.status_code}')
    print("count:", count)
    with open('./data/menu_items.json', 'w') as json_file:
        json.dump(menu_items, json_file, indent=4)


if __name__ == "__main__":
    run()
