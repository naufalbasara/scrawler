from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

import logging, time, pandas as pd, re, os

logging.basicConfig(level=logging.INFO, format='%(asctime)s -  %(levelname)s:  %(message)s')

class GMapsLocationDataScraper:
    def __init__(
            self, 
            options: dict,
        ):
        headless: bool = options.get("headless", False)
        no_sandbox: bool = options.get("no_sandbox", False)
        auto_open_devtools: bool = options.get("devtools_open", False)
        load_strategy: str = options.get("load_strategy", "normal")
        self._timeout_page_load: int = options.get("timeout_page_load", 20)
        self._delay_between_page: int = options.get("interval_page_delay", 2)
        
        self._options = webdriver.ChromeOptions()
        if headless: self._options.add_argument('--headless')
        if no_sandbox: self._options.add_argument('--no-sandbox')
        if auto_open_devtools: self._options.add_argument('auto-open-devtools-for-tabs')
        
        self._options.page_load_strategy = load_strategy
        self._webdriver = webdriver.Chrome(options=self._options)
        self._wait_driver = WebDriverWait(
            driver=self._webdriver,
            timeout=self._timeout_page_load
        )

        self._base_url = "https://www.google.com/maps"


    def __str__(self) -> str:
        return f"{self}: Google Maps Location Information Scraper"
    
    def set_creds(self, creds: dict) -> None:
        self._creds = creds

    def login(self, timeout: int = 300) -> None:
        """Open Google Maps and block until the user signs in manually in the browser window."""
        self._webdriver.get(self._base_url)

        # the account avatar links to SignOutOptions only when signed in
        signed_in_marker = (By.XPATH, "//a[contains(@href, 'accounts.google.com/SignOutOptions')]")
        logging.info(f"Please sign in to Google in the browser window (waiting up to {timeout}s)...")
        try:
            WebDriverWait(self._webdriver, timeout, poll_frequency=1).until(EC.presence_of_element_located(signed_in_marker))
        except TimeoutException:
            logging.error("Login timeout. Please check your credentials or network connection.")
            raise
        logging.info("Google login detected.")

    def crawl_all_location_by_keyword(self, keywords: list[str], target_locations: list[str]):
        self._search_url = self._base_url + "/search/"
        self._results_location = []

        for location in target_locations:
            logging.info(f"Focus finding on location: {location} for {len(keywords)} keywords...")
            for i, keyword in enumerate(keywords):
                search_location_place = f"{keyword} in {location}"
                logging.info(f"Searching for ({i+1}/{len(keywords)}) {search_location_place}...")
                search_url = self._search_url + search_location_place.replace(" ", "+")
                
                self._webdriver.get(search_url)

                scrollable_element = self._wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='m6QErb DxyBCb kA9KIf dS8AEf XiKgde ecceSd' and @role='feed']")))
                current_height = self._webdriver.execute_script("return arguments[0].scrollHeight", scrollable_element)

                # loop until all comments are loaded OR desired number of comments are loaded
                count = 0
                while True:
                    # scroll to load more comments
                    self._webdriver.execute_script(f"arguments[0].scrollBy(0, arguments[1])", scrollable_element, current_height)
                    
                    # delay between page scrollable elements (fetching more results)
                    time.sleep(self._delay_between_page)
                    height_after_load = self._webdriver.execute_script("return arguments[0].scrollHeight", scrollable_element)
    
                    # if timeout because comments not loaded or all comments already loaded
                    if current_height == height_after_load:
                        break
                    current_height = height_after_load

                    count += 1
                    if count == 50:
                        break

                # get all loaded data from the page source after scrolling
                soup = BeautifulSoup(scrollable_element.get_attribute("outerHTML"), "html.parser")
                # div parent element of places element
                places = soup.find_all("div", class_="Nv2PK THOPZb CpccDe")

                # Loop through each place and extract the relevant information
                for place in places:
                    name = getattr(place.find("div", class_="qBF1Pd fontHeadlineSmall"), "text", "").strip()
                    if name is None or len(name) == 0:
                        name = getattr(place.find("span", class_="xxVWCe"), "text", "").strip()

                    logging.info(f"Extracting data for place {name}...")
                    
                    # Example of raw_rating_review_price: '4.8(2,615) · Rp 75–175K'
                    raw_rating_review_price = getattr(place.find("div", class_="AJB7ye"), "text", "").strip()
                    try:
                        rating = re.search(r"([0-9.]+)\s*·", raw_rating_review_price).group(1)
                        num_reviews = re.search(r"\(([\d,]+)\)", raw_rating_review_price).group(1)
                        price_range = re.search(r"·\s*(.+)", raw_rating_review_price).group(1)
                    except:
                        rating = ""
                        num_reviews = ""
                        price_range = ""

                    address_category_parent_element = place.find_all("div", class_="W4Efsd")[2]
                    # Example of raw_address_category: 'Cafe · Jl. Cipete Dalam No.33, RT.2/RW.3'
                    raw_address_category = getattr(address_category_parent_element, "text", "").strip()
                    address = re.search(r"·\s*(.+)", raw_address_category).group(1) if "·" in raw_address_category else raw_address_category
                    place_category = re.search(r"(.+)\s*·", raw_address_category).group(1) if "·" in raw_address_category else ""
                    
                    url = place.select_one("a.hfpxzc[href]")
                    reference_url = url["href"].strip() if url else ""

                    logging.info(f"Found place: {name} | Rating: {rating} | Reviews: {num_reviews} | Price Range: {price_range} | Address: {address} | Category: {place_category} | Reference URL: {reference_url}")

                    place_metadata = {
                        "name": name,
                        "rating": rating,
                        "num_reviews": num_reviews,
                        "price_range": price_range,
                        "address": address,
                        "place_category": place_category,
                        "reference_url": reference_url,
                        "keyword": keyword,
                        "location": location
                    }

                    self._results_location.append(place_metadata)

            # Delay between keyword searches in Google Maps to avoid being blocked or rate-limited
            time.sleep(self._delay_between_page + 3)

        output_path = "data/gmaps_places.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pd.DataFrame(self._results_location).to_csv(output_path, index=False)
        logging.info(f"Saved {len(self._results_location)} places to {output_path}")
        return

    def scrape(self, urls: list[str]):
        self._results = []

        for _, url in enumerate(urls):
            logging.info(f"Scraping data from URL: {url}")
            self._webdriver.get(url)
            main_element = self._wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='m6QErb WNBkOb XiKgde ' and @role='main']")))

            soup = BeautifulSoup(main_element.get_attribute("outerHTML"), "html.parser")

            image_section = soup.find("div", class_="aGzt2e")
            if image_section:
                logging.debug("image_section found")
                image_element = image_section.find("img")
                image_src = image_element.get("src") if image_element else None
            else:
                logging.debug("image_section found")
                image_src = ""

            header_section = soup.find("div", class_="TIHn2")
            if header_section:
                logging.debug("header_section found")
                place_name = getattr(header_section.find("h1", class_="DUwDvf lfPIob"), "text", "").strip()
                place_category = getattr(header_section.find("button", class_="DkEaL"), "text", "").strip()
                place_description_text = getattr(soup.find("div", class_="PYvSYb", attrs={"jslog": True}), "text", "").strip().replace("\n", " ").replace("\"", "")
            else:
                logging.debug("header_section not found")
                place_name = ""
                place_category = ""
                place_description_text = ""

            additional_info_section = soup.find("div", class_="m6QErb XiKgde", attrs={"aria-label": re.compile(r"^Informasi")})
            address = getattr(additional_info_section.find("div", class_="Io6YTe fontBodyMedium kR99db fdkmkc"), "text", "").strip() if additional_info_section else ""

            # button = soup.select_one('button[data-item-id="address"]')
            # address = button["aria-label"].strip() if button else ""

            summarized_review_section = soup.find("div", class_="PPCwl cYOgid")
            rating = getattr(summarized_review_section.find("div", class_="fontDisplayLarge"), "text", "").strip() if summarized_review_section else ""
            num_of_reviews = getattr(summarized_review_section.find("div", class_="HHrUdb"), "text", "").strip() if summarized_review_section else ""
            
            highlighted_reviews = soup.find_all("div", class_="tBizfc fontBodyMedium")
            highlighted_reviews_text = [getattr(review.find("div", attrs={"role": "text"}), "text", "").strip() for review in highlighted_reviews]

            time.sleep(5)
            current_url = self._webdriver.current_url
            coordinates = re.search(r"@([0-9.-]+),([0-9.-]+),", current_url)
            latitude = coordinates.group(1) if coordinates else ""
            longitude = coordinates.group(2) if coordinates else ""

            metadata = {
                "place_name": place_name,
                "place_category": place_category,
                "place_description": place_description_text,
                "image_src": image_src,
                "address": address,
                "rating": rating,
                "num_of_reviews": num_of_reviews,
                "highlighted_reviews": highlighted_reviews_text,
                "latitude": latitude,
                "longitude": longitude
            }

            logging.info(f"{_+1}/{len(urls)}: {metadata}")

            self._results.append(metadata)
            time.sleep(self._delay_between_page)

        output_path = "data/places.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pd.DataFrame(self._results).to_csv(output_path, index=False)
        logging.info(f"Saved {len(self._results)} places to {output_path}")