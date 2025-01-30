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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RaadVanStateScraper:
    def __init__(self, batch_size=200, test_mode=False, year=None):
        self.base_url = "https://www.raadvanstate.nl"
        self.batch_size = batch_size
        self.test_mode = test_mode
        self.year = year or "2025"  # Default to 2025 if no year provided

        # Setup Chrome options
        chrome_options = Options()
        # Remove headless mode for debugging
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)

        # Update the navigator.webdriver flag to undefined
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Set a proper user agent
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver.implicitly_wait(10)  # Wait up to 10 seconds for elements

        if test_mode:
            logger.info("Running in test mode - will only process 10 advices")

    def __del__(self):
        """Cleanup the browser when done"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def get_overview_url(self, page=0):
        """Generate URL for overview page with filters"""
        return (f"{self.base_url}/adviezen/?zoeken=true&zoeken_term=&"
                f"pager_rows={self.batch_size}&kalenderjaar={self.year}&actualiteit=kalenderjaar&"
                f"Zoe_Selected_facet%3AStatus%20advies=42&"
                f"Zoe_Selected_facet%3ASoort%20advies=8&"
                f"Zoe_Selected_facet%3ASoort%20advies=27&"
                f"pager_page={page}")

    def get_page_content(self, url):
        """Fetch page content using Selenium"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Navigating to {url}")
                self.driver.get(url)

                # Add a small initial delay
                time.sleep(3)

                # Wait for the content to load
                try:
                    element = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ipx-pt-advies"))
                    )
                    logger.info("Found content on page")
                except TimeoutException:
                    logger.warning("Timeout waiting for content to load")
                    if attempt == max_retries - 1:
                        # Take a screenshot for debugging
                        self.driver.save_screenshot(f"error_page_{attempt}.png")
                        logger.info(f"Saved error screenshot to error_page_{attempt}.png")
                        raise

                return self.driver.page_source
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url}: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying after delay: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def parse_overview_page(self, html):
        """Parse the overview page and extract advice URLs"""
        soup = BeautifulSoup(html, 'html.parser')
        entries = soup.find_all('div', class_='ipx-pt-advies')

        results = []
        for entry in entries:
            try:
                # Find the link to the full advice
                title_elem = entry.find('h2')
                if not title_elem:
                    logger.warning("No title element found in entry")
                    continue

                link = title_elem.find('a')
                if not link:
                    logger.warning("No link found in title element")
                    continue

                url = link.get('href')
                if url:
                    url = url if url.startswith('http') else f"{self.base_url}{url}"
                else:
                    logger.warning("No URL found in link")
                    continue

                results.append({
                    'url': url,
                })

            except Exception as e:
                logger.error(f"Error parsing entry: {e}")
                continue

        logger.info(f"Found {len(results)} results on page")
        return results

    def get_advice_content(self, url):
        """Get the full text content and metadata of an individual advice"""
        try:
            self.driver.get(url)
            # Wait for content to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "volledigetekst"))
            )

            # Get the content
            content_div = self.driver.find_element(By.ID, "volledigetekst")
            content = content_div.text if content_div else None

            # Get the reference number
            try:
                kenmerk_div = self.driver.find_element(By.CLASS_NAME, "meta-value-kenmerk")
                kenmerk = kenmerk_div.text.strip() if kenmerk_div else None
            except Exception as e:
                logger.warning(f"Could not find kenmerk for {url}: {e}")
                kenmerk = None

            # Check for specific keywords
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
            except Exception as e:
                logger.warning(f"Could not find keywords for {url}: {e}")

            return {
                'content': content,
                'reference': kenmerk,
                'advice_type': advice_type
            }

        except Exception as e:
            logger.error(f"Error fetching advice content from {url}: {e}")
            return {
                'content': None,
                'reference': None,
                'advice_type': None
            }

    def scrape(self):
        """Main scraping function"""
        all_results = []
        page = 0
        processed_advices = 0

        while True:
            url = self.get_overview_url(page)
            logger.info(f"Scraping page {page + 1}")

            try:
                html = self.get_page_content(url)
                page_results = self.parse_overview_page(html)

                if not page_results:
                    logger.info("No results found on page, stopping")
                    break

                # In test mode, only take the first 10 results
                if self.test_mode:
                    remaining = 10 - len(all_results)
                    if remaining > 0:
                        page_results = page_results[:remaining]
                    else:
                        break

                # Get full text and metadata for each advice
                for result in page_results:
                    time.sleep(2)  # Be nice to the server
                    advice_data = self.get_advice_content(result['url'])
                    result.update(advice_data)  # Add content and reference to result
                    processed_advices += 1
                    logger.info(f"Processed advice {processed_advices}: {result['reference']}")

                all_results.extend(page_results)

                # Check if we've reached the last page (fewer entries than batch size)
                if len(page_results) < self.batch_size:
                    logger.info("Reached the last page with fewer entries than batch size")
                    break

                if self.test_mode and len(all_results) >= 10:
                    logger.info("Test mode: reached 10 advices, stopping")
                    break

                page += 1
                time.sleep(2)  # Be nice to the server between pages

            except Exception as e:
                logger.error(f"Error processing page {page}: {e}")
                break

        logger.info(f"Total results collected: {len(all_results)}")
        return pd.DataFrame(all_results)

def main():
    parser = argparse.ArgumentParser(description='Scrape Raad van State advices')
    parser.add_argument('--test', action='store_true', help='Run in test mode (only 10 advices)')
    parser.add_argument('--year', type=str, help='Year to scrape (e.g., 2024)', default="2025")
    args = parser.parse_args()

    scraper = RaadVanStateScraper(batch_size=200, test_mode=args.test, year=args.year)

    logger.info(f"Starting scraper for year: {args.year}")
    df = scraper.scrape()

    # Save to CSV with year in filename
    output_file = f'raad_van_state_adviezen_{args.year}_test.csv' if args.test else f'raad_van_state_adviezen_{args.year}.csv'
    df.to_csv(output_file, index=False)
    logger.info(f"Saved {len(df)} advice entries to {output_file}")

if __name__ == "__main__":
    main()
