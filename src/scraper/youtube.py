from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from scraper.generic import Scraper
import logging, time, os, csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s -  %(levelname)s:  %(message)s')

class YoutubeVideoScrapper(Scraper):
    def __init__(
            self, 
            options: dict,
            need_auth: bool = True,
            creds: dict | None = None,
            cookies: dict | None = None,
            api_key: str | None = None
        ):
        assert not need_auth or creds != None

        super().__init__(options=options, creds=creds)
        self._api_key = api_key
        self._cookies = cookies
        self._auth_url = "https://instagram.com"
        if need_auth:
            self.login()

    def __str__(self) -> str:
        return f"{self}: Youtube Video Scraper"
    
    def set_creds(self, creds: dict) -> None:
        self._creds = creds

    def scrape(self, urls: list[str], load_content_delay: int = 3, verbose: int = 0):
        logging.info(f"Starting to scrape 🚀")
        for url in urls:
            logging.info(f"Attempting to scrape URL {url}...")
            self._webdriver.get(url)
            time.sleep(self._timeout_page_load)

            comments_section = self._wait_driver.until(EC.presence_of_element_located((By.XPATH, "//*[@id=\"comments\"]")))
            self._webdriver.execute_script("arguments[0].scrollIntoView(true);", comments_section)
            time.sleep(load_content_delay)
            current_height = self._webdriver.execute_script("return arguments[0].scrollHeight", comments_section)
            while True:
                self._webdriver.execute_script("window.scrollBy(0, arguments[0].scrollHeight)", comments_section)
                time.sleep(load_content_delay)
                height_after_load = self._webdriver.execute_script("return arguments[0].scrollHeight", comments_section)

                if height_after_load == current_height:
                    break

                current_height = height_after_load
            
            soup = BeautifulSoup(comments_section.get_attribute("outerHTML"), "html.parser")
            comments = soup.find_all('ytd-comment-thread-renderer', class_=["style-scope ytd-item-section-renderer"])
            
            for comment in comments:
                comment_container = comment.find("div", id="main")
                try:
                    username = comment_container.find("span", class_=["style-scope ytd-comment-view-model style-scope ytd-comment-view-model"])
                    username_text = str(getattr(username, 'text', None)).strip().replace("\n", "").encode("utf-8")
                    content = comment_container.find("span", class_=["yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"])
                    content_text = str(getattr(content, 'text', None)).strip().replace("\n", "").encode("utf-8")
                    if verbose == 1:
                        logging.info(f"{username_text} - {content_text}")
                    self._results.append({"url": url, "username": username_text, "comment": content_text})
                except Exception as error:
                    logging.error(error)
                    break

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