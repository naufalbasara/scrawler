from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from scraper.generic import Scraper
import logging, time, os, csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s -  %(levelname)s:  %(message)s')

class InstagramPostScraper(Scraper):
    def __init__(
            self, 
            options: dict,
            need_auth: bool = True,
            creds: dict | None = None,
            cookies: dict | None = None,
            api_key: str | None = None
        ):
        assert need_auth or creds != None

        super().__init__(options=options, creds=creds)
        self._api_key = api_key
        self._cookies = cookies
        self._auth_url = "https://instagram.com"
        if need_auth:
            self.login()

    def __str__(self) -> str:
        return f"{self}: Instagram Post Scraper"
    
    def set_creds(self, creds: dict) -> None:
        self._creds = creds
    
    def login(self) -> None:
        _username = self._creds.get("username", None)
        _password = self._creds.get("password", None)
        if _username == None and _password == None: raise AttributeError("Need username and password to login")
        
        self._webdriver.get(self._auth_url)
        
        # form_element = self._wait_driver.until(EC.element_to_be_clickable((By.XPATH, "//form[@id='login_form']")))
        username_element = self._wait_driver.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='email']")))
        password_element = self._wait_driver.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='pass']")))
        time.sleep(3)
        
        username_element.send_keys(_username)
        password_element.send_keys(_password)
        password_element.submit()
        time.sleep(self._timeout_page_load)

        # Wait for the page to be redirected after login attempt
        self._wait_driver.until(EC.staleness_of(password_element))
        logging.info("Successfully logged in ✅")
    
    def scrape(self, urls: list[str], load_content_delay: int = 3, verbose: int = 0):
        logging.info(f"Starting to scrape 🚀")
        for url in urls:
            logging.info(f"Attempting to scrape URL {url}...")
            self._webdriver.get(url)
            time.sleep(self._timeout_page_load)

            scrollable = self._wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".x5yr21d.xw2csxc.x1odjw0f.x1n2onr6")))
            current_height = self._webdriver.execute_script("return arguments[0].scrollHeight", scrollable)

            while True:
                # scroll to load more comments
                self._webdriver.execute_script(f"arguments[0].scrollBy(0, arguments[1])", scrollable, current_height)
                # wait some time to load the comment(s)
                time.sleep(load_content_delay)
                height_after_load = self._webdriver.execute_script("return arguments[0].scrollHeight", scrollable)

                # if timeout because comments not loaded or all comments already loaded
                if current_height == height_after_load:
                    break

                current_height = height_after_load
            
            # Load all the comments
            soup = BeautifulSoup(scrollable.get_attribute("outerHTML"), 'html.parser')
            comments_section = soup.find('div', class_=["x78zum5 xdt5ytf x1iyjqo2"])
            comments = comments_section.find_all("div", class_=["html-div xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x9f619 xjbqb8w x78zum5 x15mokao x1ga7v0g x16uus16 xbiv7yw x1uhb9sk x1plvlek xryxfnj x1c4vz4f x2lah0s xdt5ytf xqjyukv x1qjc9v5 x1oa3qoh x1nhvcw1"], recursive=False)
            logging.info(f"Loaded {len(comments)} comments")
            
            for _, comment in enumerate(comments):
                username = str(getattr(comment.find("span", class_=["_ap3a _aaco _aacw _aacx _aad7 _aade"]), 'text', None)).strip().replace("\n", "").encode("utf-8")
                comment_element = getattr(comment.find("div", class_=["html-div xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x9f619 xjbqb8w x78zum5 x15mokao x1ga7v0g x16uus16 xbiv7yw x1uhb9sk x1plvlek xryxfnj x1c4vz4f x2lah0s xdt5ytf xqjyukv x1cy8zhl x1oa3qoh x1nhvcw1"]), 'span', None)
                content = str(getattr(comment_element, 'text', None)).strip().replace("\n", "").encode("utf-8")
                if verbose == 1:
                    logging.info(f"{username} - {content}")
                self._results.append({"url": url, "username": username, "comment": content})

            time.sleep(self._page_delay)

        logging.info(f"Fetched {len(self._results)} comments from {len(urls)} URLs ✅")

    def get_results(self):
        return self._results
    
    def export_results(self, output_file: os.PathLike | str):
        """
        Export results to CSV file

        Input:
            output_file: os.PathLike = data/comments.csv
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Url', 'Username', 'Comment'])
            
            for comment in self._results:
                current_url = comment['url']
                username = comment['username']
                comment = comment['comment']
                writer.writerow([current_url, username, comment])
            
        return output_file
    
    def get_summary(self):
        return f"Fetched {len(self._results)} comments."