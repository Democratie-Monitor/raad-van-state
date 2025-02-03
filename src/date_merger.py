import pandas as pd
import glob
import os
import logging
from datetime import datetime

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('date_merger_errors.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DateMerger:
    def __init__(self):
        self.error_count = 0
        self.processed_count = 0

    def get_year_from_filename(self, filename):
        """Extract year from filename"""
        try:
            return filename.split('_')[-1].split('.')[0]
        except Exception:
            return None

    def process_year(self, year):
        """Process a pair of files for a given year"""
        original_file = f'raad_van_state_adviezen_{year}.csv'
        analyzed_file = f'raad_van_state_adviezen_{year}_analyzed.csv'

        # Check if both files exist
        if not os.path.exists(original_file):
            logger.error(f"Original file not found: {original_file}")
            return
        if not os.path.exists(analyzed_file):
            logger.error(f"Analyzed file not found: {analyzed_file}")
            return

        try:
            # Read both CSV files
            logger.info(f"Processing files for year {year}")
            df_original = pd.read_csv(original_file)
            df_analyzed = pd.read_csv(analyzed_file)

            # Verify 'url' column exists in both files
            if 'url' not in df_original.columns or 'url' not in df_analyzed.columns:
                logger.error(f"URL column missing in files for year {year}")
                return

            # Create a dictionary of url to formatted date from original file
            date_dict = {}
            for _, row in df_original.iterrows():
                if pd.notna(row.get('datum_advies_formatted')):
                    date_dict[row['url']] = row['datum_advies_formatted']
                else:
                    logger.warning(f"No formatted date found for URL in year {year}: {row['url']}")

            # Add datum_advies_formatted column to analyzed file
            if 'datum_advies_formatted' not in df_analyzed.columns:
                df_analyzed['datum_advies_formatted'] = None

            # Update dates and log any issues
            for index, row in df_analyzed.iterrows():
                url = row['url']
                if url in date_dict:
                    df_analyzed.at[index, 'datum_advies_formatted'] = date_dict[url]
                    self.processed_count += 1
                else:
                    logger.warning(f"No date found for URL in year {year}: {url}")
                    self.error_count += 1

            # Save the updated analyzed file
            df_analyzed.to_csv(analyzed_file, index=False)
            logger.info(f"Successfully updated {analyzed_file}")

        except Exception as e:
            logger.error(f"Error processing year {year}: {e}")
            self.error_count += 1

    def process_all_files(self):
        """Process all matching CSV files"""
        try:
            # Find all original files
            csv_pattern = 'raad_van_state_adviezen_????.csv'
            original_files = glob.glob(csv_pattern)

            # Process each year
            for file in original_files:
                year = self.get_year_from_filename(file)
                if year and year.isdigit() and len(year) == 4:
                    self.process_year(year)

            # Log summary
            logger.info(f"Processing completed:")
            logger.info(f"Total records processed: {self.processed_count}")
            logger.info(f"Total errors encountered: {self.error_count}")

        except Exception as e:
            logger.error(f"Error in process_all_files: {e}")

def main():
    merger = DateMerger()
    merger.process_all_files()

if __name__ == "__main__":
    main()
