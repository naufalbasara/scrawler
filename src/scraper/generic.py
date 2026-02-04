from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s -  %(levelname)s:  %(message)s')
load_dotenv()

class Scraper(ABC):
    def __init__(self, options: dict, creds: dict):
        logging.info("Initiating scraper...")
        headless: bool = options.get("headless", False)
        no_sandbox: bool = options.get("no_sandbox", False)
        auto_open_devtools: bool = options.get("devtools_open", False)
        load_strategy: str = options.get("load_strategy", "normal")
        self._timeout_page_load: int = options.get("timeout_page_load", 20)
        self._page_delay: int = options.get("interval_page_delay", 2)
        
        self._options = webdriver.ChromeOptions()
        if headless: self._options.add_argument('--headless')
        if no_sandbox: self._options.add_argument('--no-sandbox')
        if auto_open_devtools: self._options.add_argument('auto-open-devtools-for-tabs')
        
        self._options.page_load_strategy = load_strategy
        self._webdriver = webdriver.Chrome(options=self._options)
        self._wait_driver = WebDriverWait(driver=self._webdriver, timeout=self._timeout_page_load)
        self._results = []
        self._creds = creds

    @abstractmethod
    def scrape(self, urls: list[str]):
        """Receive input of URLs of certain platform type that will be crawled and fetched.

        Input:
            urls: list[str] = ["https://url1.co.id", "https://url2.co.id", "https://url3.co.id"]
        """
        pass
    
    @abstractmethod
    def get_summary(self):
        """Get summary of the scraper after scrape() called"""
        pass
    
    @abstractmethod
    def get_results(self):
        """Get results of the data that being fetched after scraping"""
        pass