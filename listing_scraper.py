from dataclasses import dataclass
import os
import random
from typing import List, Optional, Tuple
from selenium import webdriver
import time
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
import json
import uuid
import tqdm
import logging
from selenium.webdriver.chrome.options import Options


@dataclass(frozen=True)
class Listing:
    url: str
    img_url: str
    title: str
    id: int

    # support JSON serialization
    def to_json(self):
        return {
            'url': self.url,
            'img_url': self.img_url,
            'title': self.title,
            'id': self.id
        }


@dataclass(frozen=True)
class ScrapedListing:
    make: str
    model: str
    year: int
    kilometers: int
    import_history: str
    fuel_economy: float
    description: str

    # support JSON serialization
    def to_json(self):
        return {
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'kilometers': self.kilometers,
            'import_history': self.import_history,
            'litres_per_100_km': self.fuel_economy,
            'description': self.description
        }


def create_driver() -> WebDriver:
    # Create a new instance of the Chrome driver
    chrome_options = Options()
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def scroll_to_bottom(driver: WebDriver):
    SCROLL_STEPS = 30
    SCROLL_PAUSE_TIME = 1.5 / SCROLL_STEPS

    # Get the final scroll height
    final_height = driver.execute_script("return document.body.scrollHeight")

    for step in range(SCROLL_STEPS):
        # Calculate the scroll distance for each step
        scroll_distance = final_height * (step + 1) / SCROLL_STEPS

        # Perform the scroll action
        driver.execute_script(f"window.scrollTo(0, {scroll_distance});")
        time.sleep(SCROLL_PAUSE_TIME)


def scrape_scrollview(driver: WebDriver, url: str) -> Tuple[List[Listing], Optional[str]]:
    # get page source
    driver.get(url)
    time.sleep(2)  # give time for all elements to load

    scroll_to_bottom(driver)

    time.sleep(1)

    # Find all the listing links on the page
    listings = driver.find_elements(By.CSS_SELECTOR, 'a.tm-motors-search-card__link')

    listings_data = []
    for listing in listings:
        # Get the href attribute of the link, which contains the URL of the listing
        listing_url = listing.get_attribute('href')

        # Get the image element within the listing
        img = listing.find_element(By.CSS_SELECTOR, 'img.tm-progressive-image-loader__full')

        # Get the src attribute of the image, which contains the URL of the image
        img_url = img.get_attribute('src')

        # Get the title of the listing
        title = listing.find_element(By.CSS_SELECTOR, 'div.tm-motors-search-card__title').text

        listings_data.append(Listing(listing_url, img_url, title, uuid.uuid4().int))

    # Find the next page button
    try:
        link = driver.find_element(By.CSS_SELECTOR, '.o-pagination__nav-item--last a')

        if link.text == 'Next':
            # Get the href attribute of the link, which contains the URL of the next page
            next_url = link.get_attribute('href')
        else:
            next_url = None
    except selenium.common.exceptions.NoSuchElementException:
        next_url = None

    print(f"Found {len(listings_data)} listings on page {url}")

    return listings_data, next_url


def extract_make(driver: WebDriver) -> str:
    try:
        breadcrumb_element = driver.find_element(By.CSS_SELECTOR, ".tm-breadcrumbs.o-breadcrumbs")

        # Get all list items within the breadcrumb
        list_items = breadcrumb_element.find_elements(By.CSS_SELECTOR, "li.o-breadcrumbs__item")

        # the second last list item is the make
        return list_items[-2].text
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find make")
        return 'Unknown'
    except IndexError:
        logging.warning("Could not find make due to missing index")
        return 'Unknown'


def extract_model(driver: WebDriver) -> str:
    try:
        breadcrumb_element = driver.find_element(By.CSS_SELECTOR, ".tm-breadcrumbs.o-breadcrumbs")

        # Get all list items within the breadcrumb
        list_items = breadcrumb_element.find_elements(By.CSS_SELECTOR, "li.o-breadcrumbs__item")

        # the last list item is the model
        return list_items[-1].text
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find model")
        return 'Unknown'
    except IndexError:
        logging.warning("Could not find model due to missing index")
        return 'Unknown'


def extract_year(driver: WebDriver) -> int:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, '.tm-motors-vehicle-attributes__tag')

        for element in elements:
            # Check if 'Year:' is in the inner text of the element
            if 'Year:' in element.text:
                year = element.text.strip().replace('Year:', '')
                return int(year)
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find year element")
    logging.warning("Could not find year")
    return -1


def strip_element_text(element_text: str) -> Optional[str]:
    # strip everything up until the first digit, and after the last digit
    digit_start = None
    digit_end = None
    for i, char in enumerate(element_text):
        if char.isdigit():
            digit_start = i
            break
    for i in range(len(element_text) - 1, -1, -1):
        if element_text[i].isdigit():
            digit_end = i
            break

    if digit_start is not None and digit_end is not None:
        return element_text[digit_start:digit_end + 1].replace(',', '')
    else:
        return None


def extract_kilometers(driver: WebDriver) -> int:
    try:
        element = driver.find_element(By.XPATH, "//tg-icon[@name='vehicle-odometer']/ancestor::tg-tag")
        element_text = element.text.strip().replace(',', '').replace('km', '')
        # strip everything up until the first digit, and after the last digit
        element_text = strip_element_text(element_text)
        if element_text is not None:
            return int(element_text)
        logging.warning("Could not find kilometers")
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find kilometers")
    return -1


def extract_import_history(driver: WebDriver) -> str:
    try:
        tag_elements = driver.find_elements(By.CSS_SELECTOR, "tg-tag.tm-motors-vehicle-attributes__tag.o-tag")
        for element in tag_elements:
            # Check if 'Import history:' is in the inner text of the element
            if 'Import history:' in element.text:
                print(element.text)
                text = element.text.strip().replace('Import history:', '')
                if "NZ New" in text:
                    return "NZ New"
                return "Imported"
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find import history")
    logging.warning("Could not find import history due to missing element")
    return 'Unknown'


def extract_fuel_economy(driver: WebDriver) -> float:
    try:
        fuel_economy_rating = driver.find_element(By.CSS_SELECTOR, ".tm-motors-listing-ratings__fuel")
        return float(fuel_economy_rating.text.strip().replace(' ', '').replace('L/100km', ''))
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find fuel economy")
        return -1


def scrape_listing(driver: WebDriver, listing: Listing) -> ScrapedListing:
    print(f"Scraping listing {listing.url}...")

    os.makedirs(f'listings/{listing.id}', exist_ok=True)

    driver.get(listing.url)
    time.sleep(2.5)  # give time for all elements to load

    # click to load more description
    try:
        element = driver.find_element(By.CSS_SELECTOR, '.tm-motors-listing-body__item-show-more-button.o-transparent-button2')
        # scroll to the element
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(0.5)
        # click the element
        element.click()
    except selenium.common.exceptions.NoSuchElementException:
        logging.warning("Could not find show more button")
    except selenium.common.exceptions.ElementClickInterceptedException:
        logging.warning("Could not click show more button as the click was intercepted!")

    # capture image of the listing
    driver.save_screenshot(f'listings/{listing.id}/0.png')

    scroll_to_bottom(driver)

    time.sleep(1.5)

    # save the source to a file
    with open(f'listings/{listing.id}/page.html', 'w') as f:
        f.write(driver.page_source)

    # capture image of the listing
    driver.save_screenshot(f'listings/{listing.id}/1.png')

    # save the description
    # description_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.tm-markdown')))
    description_element = driver.find_element(By.CSS_SELECTOR, '.tm-markdown')

    # Extract the description
    description_text = description_element.text

    # extract data from the listing
    scraped_listing = ScrapedListing(
        make=extract_make(driver),
        model=extract_model(driver),
        year=extract_year(driver),
        kilometers=extract_kilometers(driver),
        import_history=extract_import_history(driver),
        fuel_economy=extract_fuel_economy(driver),
        description=description_text
    )

    with open(f'listings/{listing.id}/data.json', 'w') as f:
        json.dump({
            'listing': listing.to_json(),
            'scraped_listing': scraped_listing.to_json()
        }, f, indent=4)

    return scraped_listing


def main():
    print("Scraping listings...")
    driver = create_driver()
    listings: List[Listing] = []

    if os.path.exists('listings.json'):
        print("Found existing listings.json file, loading...")
        with open('listings.json', 'r') as f:
            listings = [Listing(**item) for item in json.load(f)]
        print(f"Loaded {len(listings)} listings from file.")

    scrape_listview = True
    if len(listings) > 0:
        print("Found existing listings, would you like to rescan for new listings? (y/N)")
        if input().lower() != 'y':
            scrape_listview = False

    if scrape_listview:
        maybe_next: Optional[str] = "https://www.trademe.co.nz/a/motors/cars/plug-in-hybrid"
        while True:
            page_items, maybe_next = scrape_scrollview(driver, maybe_next)
            listings.extend(page_items)
            if maybe_next is None:
                break

        # deduplicate listings
        listings = list(set(listings))

        with open('listings.json', 'w') as f:
            json.dump([item.to_json() for item in listings], f, indent=4)

    # process each listing
    print("Scraping individual listings...")
    for listing in tqdm.tqdm(listings):
        scrape_listing(driver, listing)
        # wait between 1 and 10 seconds
        time.sleep(random.randint(1, 300) / 100)

    print("Done!")
    driver.quit()


if __name__ == "__main__":
    main()
