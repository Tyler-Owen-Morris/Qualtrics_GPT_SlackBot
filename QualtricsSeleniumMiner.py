from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup
driver = webdriver.Firefox()  # or whichever browser you prefer

# Navigate to the website
driver.get(
    'https://www.qualtrics.com/support/survey-platform/information-survey-takers/')

# Find the nav element
nav = driver.find_element(By.TAG_NAME, 'nav')

# Find all list items in the nav
list_items = nav.find_elements_by_tag_name('li')

# Iterate through each list item
for item in list_items:
    # Click the item to expand it
    item.click()

    # Find all links in the expanded item
    links = item.find_elements_by_tag_name('a')

    # Iterate through each link
    for link in links:
        try:
            # Click the link and wait for the page to load
            link.click()
            driver.implicitly_wait(10)  # wait for 10 seconds

            # Validate the page loaded successfully
            # (You'll add your own validation code here)

        except NoSuchElementException:
            # Log the error
            print(f"Error loading {link.get_attribute('href')}")

# Cleanup
driver.quit()
