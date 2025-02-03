# Raad van State Scraper and Analyzer

This repository contains a web scraper and analyzer for the Dutch Raad van State (Council of State) advices. Replicate serverless LLM API is used, for analysis by Llama3.2.

## Features

- Scrapes advices from the Raad van State website for a specified year
- Analyzes the scraped advices and categorizes them based on standard dictum formulations
- Provides reasoning for the categorization
- Saves the scraped and analyzed data to CSV files
- Validates date fields, formats text dates into dd-mm-yyyy
- Merges all seperate years into one giant CSV file

## Categories

The analyzer categorizes the advices into the following categories based on standard dictum formulations:

- Category A: No remarks, advice to submit to the Tweede Kamer.
- Category B: Some remarks, advice to consider before submitting to the Tweede Kamer.
- Category C: Objections, advice not to submit to the Tweede Kamer unless adapted.
- Category D: Serious objections, advice not to submit to the Tweede Kamer.
- Category E: Old style - positive, no or few remarks, advice to submit to the Tweede Kamer.
- Category F: Old style - critical, advice to adapt or not submit to the Tweede Kamer.
- Category G: Unclear or no final assessment found.

## Scraped Data Structure

The scraper collects the following information for each advice:

- URL: The URL of the advice on the Raad van State website.
- Content: The full text content of the advice.
- Reference: The reference number (kenmerk) of the advice.
- Advice Type: The type of advice (Wet or Algemene maatregel van bestuur).
- Date Aanhanging: Day of "aanhanging" in text format
- Date Vaststelling: Day of "vaststelling" in text format
- Date Advies: Day of "advies" in text format
- Date Publicatie: Day of "publicatie" in text format

The scraped data is saved in a CSV file named `raad_van_state_adviezen_<year>.csv`.

Afterwards the validator script changes the date format into machine readable format:
- Date Advies Formatted: Day of advies formatted in dd-mm-yyyy form

## Installation

1. Clone the repository:
```
git clone https://github.com/Democratie-Monitor/raad-van-state.git
```
2. Install the required dependencies:
```
pip install -r requirements.txt
```
3. Set up the necessary environment variables:
- `REPLICATE_API_TOKEN`: Your Replicate API token for using the language model.

## Usage

### 1. Run the scraper to fetch advices for a specific year (default is 2025):
```
python src/scraper.py --year 2025
```
Optional arguments:
- `--test`: Run in test mode to scrape only 10 advices.
- `--year`: Specify the year to scrape advices for (e.g., 2024).

### 2. Run the analyzer to categorize the scraped advices:
```
python src/analyzer.py data/raad_van_state_adviezen_2025.csv
```
Optional arguments:
- `--test`: Run in test mode to analyze only 10 advices.
- `--start-row`: Start processing from a specific row number.

This will result in a raad_van_state_adviezen_YYYY_analyzed.csv file

### 3. Run the date validator to check date fields and format into dd-mm-yyyy:

This script processes all RvS advice CSV files in the current directory and adds formatted date columns.

```
python src/validator.py
```
No arguments needed - the script will:
- Find all files matching 'raad_van_state_adviezen_*.csv'
- Convert Dutch format dates to dd-mm-yyyy format
- Create new columns with '_formatted' suffix
- Prompt for manual input when datum_advies cannot be automatically converted

### 4. Transfers date information from original RvS advice CSV files to their analyzed counterparts.

```
python date_merger.py
```

No arguments needed - the script will:
- Find pairs of files like 'raad_van_state_adviezen_YYYY.csv' and 'raad_van_state_adviezen_YYYY_analyzed.csv'
- Copy the 'datum_advies_formatted' column from the original to the analyzed file
- Create a log file 'date_merger_errors.log' with details of any issues encountered
- Process all years found in the current directory

File requirements:
- Original files should be named: raad_van_state_adviezen_YYYY.csv
- Analyzed files should be named: raad_van_state_adviezen_YYYY_analyzed.csv

### 5. View the scraped and analyzed data in your directory.

Do a couple of manual checks to make sure everything went as expected.

### 6. Merge all CSV into one giant file
   
This script combines all analyzed RvS advice CSV files into a single comprehensive CSV file.

```
python csv_merger.py
```

No arguments needed - the script will:
- Find all files matching '*_analyzed.csv' in the current directory
- Merge them into a single CSV file
- Add a 'source_file' column to track the origin of each row
- Create detailed logs in 'merger_log.log'
- Output file will be named: merged_raad_van_state_adviezen_YYYYMMDD.csv (using current date)

Features:
- Verifies column consistency across files
- Detects and logs duplicate URLs
- Preserves all original data
- Creates summary statistics of the merge operation

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvement, please open an issue or submit a pull request.

## License

This project is licensed under the GNU GPL v3
