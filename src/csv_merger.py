import pandas as pd
import glob
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('merger_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CSVMerger:
    def __init__(self):
        self.total_rows = 0
        self.output_filename = f'merged_raad_van_state_adviezen_{datetime.now().strftime("%Y%m%d")}.csv'

    def verify_columns(self, dataframes):
        """Verify that all dataframes have the same columns"""
        if not dataframes:
            return None

        reference_columns = set(dataframes[0].columns)
        mismatched_files = []

        for i, df in enumerate(dataframes[1:], 1):
            if set(df.columns) != reference_columns:
                filename = f'file_{i+1}'  # Since we don't have filenames here
                mismatched_files.append(filename)
                logger.warning(f"Column mismatch in {filename}")
                logger.warning(f"Expected: {sorted(reference_columns)}")
                logger.warning(f"Found: {sorted(df.columns)}")

        return len(mismatched_files) == 0

    def merge_files(self):
        """Merge all analyzed CSV files"""
        try:
            # Find all analyzed CSV files
            pattern = '*_analyzed.csv'
            csv_files = glob.glob(pattern)

            if not csv_files:
                logger.error("No analyzed CSV files found")
                return False

            logger.info(f"Found {len(csv_files)} CSV files to merge")

            # Read all CSVs into a list of dataframes
            dataframes = []
            for file in sorted(csv_files):  # Sort to ensure consistent order
                try:
                    logger.info(f"Reading {file}")
                    df = pd.read_csv(file)
                    df['source_file'] = os.path.basename(file)  # Add source file information
                    dataframes.append(df)
                    logger.info(f"Added {len(df)} rows from {file}")
                except Exception as e:
                    logger.error(f"Error reading {file}: {e}")
                    continue

            if not dataframes:
                logger.error("No data frames were successfully read")
                return False

            # Verify columns match
            if not self.verify_columns(dataframes):
                logger.error("Column mismatch detected between files")
                return False

            # Merge all dataframes
            logger.info("Merging dataframes...")
            merged_df = pd.concat(dataframes, ignore_index=True)
            self.total_rows = len(merged_df)

            # Check for duplicates
            duplicate_count = merged_df.duplicated(subset=['url']).sum()
            if duplicate_count > 0:
                logger.warning(f"Found {duplicate_count} duplicate URLs in the merged data")

            # Save merged dataframe
            logger.info(f"Saving merged data to {self.output_filename}")
            merged_df.to_csv(self.output_filename, index=False)

            # Log summary statistics
            logger.info("\nMerge Summary:")
            logger.info(f"Total files processed: {len(dataframes)}")
            logger.info(f"Total rows in merged file: {self.total_rows}")
            logger.info(f"Number of duplicate URLs: {duplicate_count}")
            logger.info(f"Output saved to: {self.output_filename}")

            return True

        except Exception as e:
            logger.error(f"Error in merge_files: {e}")
            return False

def main():
    merger = CSVMerger()
    merger.merge_files()

if __name__ == "__main__":
    main()
