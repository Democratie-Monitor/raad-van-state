import pandas as pd
import glob
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DateValidator:
    def __init__(self):
        self.date_format = "%d-%m-%Y"  # Target format: dd-mm-yyyy
        # Dutch month names mapping (all lowercase)
        self.dutch_months = {
            'januari': '01', 'februari': '02', 'maart': '03', 'april': '04',
            'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08',
            'september': '09', 'oktober': '10', 'november': '11', 'december': '12',
            # Add common variations
            'aug': '08', 'aug.': '08', 'sept': '09', 'sept.': '09',
            'okt': '10', 'okt.': '10', 'nov': '11', 'nov.': '11',
            'dec': '12', 'dec.': '12', 'jan': '01', 'jan.': '01',
            'feb': '02', 'feb.': '02', 'mrt': '03', 'mrt.': '03'
        }

    def parse_dutch_date(self, date_str):
        """Parse a date string with Dutch month name into dd-mm-yyyy format"""
        if pd.isna(date_str):
            return None

        try:
            # Split the date string into components and convert to lowercase
            parts = [part.strip().lower() for part in str(date_str).split()]
            if len(parts) != 3:
                logger.debug(f"Unexpected date format: {date_str} (not 3 parts)")
                return None

            day = parts[0].zfill(2)  # Pad single-digit days with leading zero
            month = self.dutch_months.get(parts[1])
            year = parts[2]

            if not all([day, month, year]):
                return None

            # Validate the date
            datetime.strptime(f"{day}-{month}-{year}", self.date_format)
            return f"{day}-{month}-{year}"
        except (ValueError, IndexError):
            return None

    def prompt_for_date(self, url, current_value):
        """Prompt user for a valid date"""
        print(f"\nURL: {url}")
        print(f"Current value: {current_value}")

        while True:
            date_input = input("Please enter the correct date (dd-mm-yyyy) or 'skip' to skip: ")

            if date_input.lower() == 'skip':
                return None

            try:
                datetime.strptime(date_input, self.date_format)
                return date_input
            except ValueError:
                print("Invalid date format. Please use dd-mm-yyyy format (e.g., 01-01-2024)")

    def process_file(self, file_path):
        """Process a single CSV file"""
        try:
            logger.info(f"Processing file: {file_path}")

            # Read the CSV file
            df = pd.read_csv(file_path)

            # Create new formatted date columns
            date_columns = ['datum_aanhangig', 'datum_vaststelling', 'datum_advies', 'datum_publicatie']
            formatted_columns = [f"{col}_formatted" for col in date_columns]

            # Initialize new columns
            for new_col in formatted_columns:
                if new_col not in df.columns:
                    df[new_col] = None

            # Process each row
            changes_made = False
            for index, row in df.iterrows():
                # Process each date column
                for orig_col, new_col in zip(date_columns, formatted_columns):
                    current_date = row.get(orig_col)

                    # Try to parse the Dutch date
                    formatted_date = self.parse_dutch_date(current_date)

                    # If parsing failed and it's datum_advies, prompt for manual entry
                    if formatted_date is None and orig_col == 'datum_advies':
                        formatted_date = self.prompt_for_date(row['url'], current_date)
                        if formatted_date:
                            changes_made = True

                    # Store the formatted date
                    df.at[index, new_col] = formatted_date

                # Save progress periodically
                if changes_made and index % 10 == 0:
                    df.to_csv(file_path, index=False)
                    logger.info(f"Saved progress after row {index}")

            # Final save
            df.to_csv(file_path, index=False)
            logger.info(f"Completed processing {file_path}")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

    def process_all_files(self):
        """Process all matching CSV files in the current directory"""
        try:
            # Find all matching CSV files
            csv_pattern = 'raad_van_state_adviezen_*.csv'
            csv_files = glob.glob(csv_pattern)

            if not csv_files:
                logger.error(f"No CSV files found matching pattern: {csv_pattern}")
                return

            logger.info(f"Found {len(csv_files)} CSV files to process")

            # Process each file
            for csv_file in csv_files:
                self.process_file(csv_file)

        except Exception as e:
            logger.error(f"Error in process_all_files: {e}")

def main():
    validator = DateValidator()
    validator.process_all_files()

if __name__ == "__main__":
    main()
