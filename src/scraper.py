import time
import pandas as pd
from bs4 import BeautifulSoup
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import argparse

# Enhanced logging configuration with milliseconds
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed output
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class RaadVanStateScraper:
    def __init__(self, batch_size=200, test_mode=False, year=None):
        start_time = time.time()
        logger.info("Initializing scraper...")

        self.base_url = "https://www.raadvanstate.nl"
        self.batch_size = batch_size
        self.test_mode = test_mode
        self.year = year or "2025"

        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        # Add headless mode for faster operation
        chrome_options.add_argument('--headless')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        logger.debug("Chrome options configured, initializing driver...")

        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)

        # Update the navigator.webdriver flag to undefined
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Set a proper user agent
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Reduce implicit wait time from 10 to 5 seconds
        self.driver.implicitly_wait(5)

        init_time = time.time() - start_time
        logger.info(f"Scraper initialization completed in {init_time:.2f} seconds")

        if test_mode:
            logger.info("Running in test mode - will only process 10 advices")

    def get_overview_url(self, page=0):
        """Generate URL for overview page with filters"""
        url = (f"{self.base_url}/adviezen/?zoeken=true&zoeken_term=&"
                f"pager_rows={self.batch_size}&kalenderjaar={self.year}&actualiteit=kalenderjaar&"
                f"Zoe_Selected_facet%3AStatus%20advies=42&"
                f"Zoe_Selected_facet%3ASoort%20advies=8&"
                f"Zoe_Selected_facet%3ASoort%20advies=27&"
                f"pager_page={page}")
        logger.info(f"Generated URL for year {self.year}, page {page}: {url}")
        return url

    def get_page_content(self, url):
        """Fetch page content using Selenium with enhanced timing information"""
        start_time = time.time()
        logger.info(f"Navigating to {url}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                page_load_start = time.time()
                self.driver.get(url)
                page_load_time = time.time() - page_load_start
                logger.debug(f"Initial page load took {page_load_time:.2f} seconds")

                # Wait for content with timeout
                try:
                    wait_start = time.time()
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ipx-pt-advies"))
                    )
                    wait_time = time.time() - wait_start
                    logger.debug(f"Content wait completed in {wait_time:.2f} seconds")
                except TimeoutException:
                    logger.warning("Content wait timed out after 2 seconds")

                total_time = time.time() - start_time
                logger.info(f"Page content fetch completed in {total_time:.2f} seconds")
                return self.driver.page_source

            except Exception as e:
                retry_time = time.time() - start_time
                logger.error(f"Attempt {attempt + 1} failed after {retry_time:.2f} seconds: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def parse_overview_page(self, html):
        """Parse the overview page and extract advice URLs"""
        start_time = time.time()
        logger.debug("Starting to parse overview page")

        # Log a snippet of the HTML to see what we're getting
        logger.debug(f"First 500 characters of HTML: {html[:500]}")

        # Check if we got any content at all
        if not html or len(html.strip()) == 0:
            logger.error("Received empty HTML content")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        entries = soup.find_all('div', class_='ipx-pt-advies')

        logger.debug(f"Found {len(entries)} entries to process")
        results = []
        for i, entry in enumerate(entries, 1):
            entry_start = time.time()
            try:
                title_elem = entry.find('h2')
                if not title_elem:
                    logger.warning(f"No title element found in entry {i}")
                    continue

                link = title_elem.find('a')
                if not link:
                    logger.warning(f"No link found in title element for entry {i}")
                    continue

                url = link.get('href')
                if url:
                    url = url if url.startswith('http') else f"{self.base_url}{url}"
                else:
                    logger.warning(f"No URL found in link for entry {i}")
                    continue

                results.append({
                    'url': url,
                })
                entry_time = time.time() - entry_start
                logger.debug(f"Processed entry {i} in {entry_time:.2f} seconds")

            except Exception as e:
                logger.error(f"Error parsing entry {i}: {e}")
                continue

        total_time = time.time() - start_time
        logger.info(f"Found {len(results)} results on page in {total_time:.2f} seconds")
        return results

    def get_advice_dates(self):
        """Extract date metadata from the current page with optimized performance"""
        start_time = time.time()
        logger.debug("Starting to extract dates")

        dates = {
            'datum_aanhangig': None,
            'datum_vaststelling': None,
            'datum_advies': None,
            'datum_publicatie': None
        }

        # Define date fields we're looking for
        metadata_map = {
            'meta-value-datum-aanhangig': 'datum_aanhangig',
            'meta-value-datum-vaststelling': 'datum_vaststelling',
            'meta-value-datum-advies': 'datum_advies',
            'meta-value-datum-publicatie': 'datum_publicatie'
        }

        try:
            # Use a shorter implicit wait temporarily for faster negative results
            original_wait = self.driver.timeouts.implicit_wait
            self.driver.implicitly_wait(1)

            # Find all date elements in one go using a CSS selector
            selector = ', '.join(f'.{class_name}' for class_name in metadata_map.keys())
            date_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

            # Process found date elements
            found_dates = []
            for element in date_elements:
                # Get the class name to identify which date field this is
                class_name = None
                for possible_class in metadata_map.keys():
                    if possible_class in element.get_attribute('class'):
                        class_name = possible_class
                        break

                if class_name:
                    try:
                        date_text = element.text.strip()
                        if date_text:
                            dict_key = metadata_map[class_name]
                            dates[dict_key] = date_text
                            found_dates.append(class_name)
                            logger.debug(f"Found date {dict_key}: {date_text}")
                    except Exception as e:
                        logger.warning(f"Error extracting text from date element: {e}")

            # Reset the implicit wait to original value
            self.driver.implicitly_wait(original_wait)

            total_time = time.time() - start_time
            if found_dates:
                logger.info(f"Found dates: {', '.join(found_dates)} in {total_time:.2f} seconds")
            else:
                logger.warning(f"No dates found after {total_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Error during date extraction: {e}")
            # Reset the implicit wait to original value in case of error
            self.driver.implicitly_wait(original_wait)

        return dates

    def get_advice_content(self, url):
        """Get the full text content and metadata of an individual advice"""
        start_time = time.time()
        logger.info(f"Starting to fetch advice content from {url}")

        try:
            page_load_start = time.time()
            self.driver.get(url)
            logger.debug(f"Page load took {time.time() - page_load_start:.2f} seconds")

            # Wait for content
            try:
                wait_start = time.time()
                WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.ID, "volledigetekst"))
                )
                logger.debug(f"Content wait took {time.time() - wait_start:.2f} seconds")
            except TimeoutException:
                logger.warning("Content wait timed out after 2 seconds")

            # Get the content
            content_start = time.time()
            content_div = self.driver.find_element(By.ID, "volledigetekst")
            content = content_div.text if content_div else None
            logger.debug(f"Content extraction took {time.time() - content_start:.2f} seconds")

            # Get the reference number
            ref_start = time.time()
            try:
                kenmerk_div = self.driver.find_element(By.CLASS_NAME, "meta-value-kenmerk")
                kenmerk = kenmerk_div.text.strip() if kenmerk_div else None
                logger.debug(f"Reference extraction took {time.time() - ref_start:.2f} seconds")
            except Exception as e:
                logger.warning(f"Could not find kenmerk: {e}")
                kenmerk = None

            # Get advice type
            type_start = time.time()
            advice_type = None
            try:
                keywords_ul = self.driver.find_element(By.CLASS_NAME, "trefwoorden")
                keywords_items = keywords_ul.find_elements(By.TAG_NAME, "li")

                for item in keywords_items:
                    title = item.get_attribute('title')
                    if title == "Soort advies Wet":
                        advice_type = "Wet"
                        break
                    elif title == "Soort advies Algemene maatregel van bestuur":
                        advice_type = "AMVB"
                        break
                logger.debug(f"Advice type extraction took {time.time() - type_start:.2f} seconds")
            except Exception as e:
                logger.warning(f"Could not find keywords: {e}")

            # Get dates
            dates_start = time.time()
            dates = self.get_advice_dates()
            logger.debug(f"Dates extraction took {time.time() - dates_start:.2f} seconds")

            total_time = time.time() - start_time
            logger.info(f"Completed fetching advice content in {total_time:.2f} seconds")

            return {
                'content': content,
                'reference': kenmerk,
                'advice_type': advice_type,
                **dates  # Unpack all date fields
            }

        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"Error fetching advice content after {error_time:.2f} seconds: {e}")
            return {
                'content': None,
                'reference': None,
                'advice_type': None,
                'datum_aanhangig': None,
                'datum_vaststelling': None,
                'datum_advies': None,
                'datum_publicatie': None
            }

    def scrape(self):
        """Main scraping function"""
        start_time = time.time()
        logger.info(f"Starting scraping process for year {self.year}")

        # First verify the year is valid
        if not (1900 <= int(self.year) <= 2025):
            logger.error(f"Invalid year {self.year}. Please check the year is correct.")
            return pd.DataFrame()

        all_results = []
        page = 0
        processed_advices = 0

        while True:
            page_start = time.time()
            url = self.get_overview_url(page)
            logger.info(f"Scraping page {page + 1}")

            try:
                html = self.get_page_content(url)
                page_results = self.parse_overview_page(html)

                if not page_results:
                    logger.info("No results found on page, stopping")
                    break

                if self.test_mode:
                    remaining = 10 - len(all_results)
                    if remaining > 0:
                        page_results = page_results[:remaining]
                        logger.debug(f"Test mode: limited to {remaining} results")
                    else:
                        break

                for i, result in enumerate(page_results, 1):
                    advice_start = time.time()
                    time.sleep(1)  # Reduced delay between requests
                    advice_data = self.get_advice_content(result['url'])
                    result.update(advice_data)
                    processed_advices += 1
                    advice_time = time.time() - advice_start
                    logger.info(f"Processed advice {processed_advices} ({result['reference']}) in {advice_time:.2f} seconds")

                all_results.extend(page_results)

                if len(page_results) < self.batch_size:
                    logger.info("Reached the last page with fewer entries than batch size")
                    break

                if self.test_mode and len(all_results) >= 10:
                    logger.info("Test mode: reached 10 advices, stopping")
                    break

                page += 1
                page_time = time.time() - page_start
                logger.info(f"Completed page {page} in {page_time:.2f} seconds")
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error processing page {page}: {e}")
                break

        total_time = time.time() - start_time
        logger.info(f"Total scraping completed in {total_time:.2f} seconds. Collected {len(all_results)} results.")
        return pd.DataFrame(all_results)

def main():
    print("Starting main function")  # Basic print for debugging
    parser = argparse.ArgumentParser(description='Scrape Raad van State advices')
    parser.add_argument('--test', action='store_true', help='Run in test mode (only 10 advices)')
    parser.add_argument('--year', type=str, help='Year to scrape (e.g., 2024)', default="2025")
    args = parser.parse_args()

    print(f"Arguments received: test={args.test}, year={args.year}")  # Print arguments

    try:
        start_time = time.time()
        logger.info(f"Starting scraper for year: {args.year}")

        scraper = RaadVanStateScraper(batch_size=200, test_mode=args.test, year=args.year)
        df = scraper.scrape()

        # Save to CSV with year in filename
        output_file = f'raad_van_state_adviezen_{args.year}_test.csv' if args.test else f'raad_van_state_adviezen_{args.year}.csv'
        df.to_csv(output_file, index=False)

        total_time = time.time() - start_time
        logger.info(f"Saved {len(df)} advice entries to {output_file}. Total runtime: {total_time:.2f} seconds")
    except Exception as e:
        print(f"An error occurred: {str(e)}")  # Print any errors
        raise  # Re-raise the exception to see the full traceback

print("Starting __main__")
if __name__ == "__main__":
    print("Script is starting...")
    main()
    print("Script completed")
