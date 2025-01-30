# Raad van State Scraper and Analyzer

This repository contains a web scraper and analyzer for the Dutch Raad van State (Council of State) advices.

## Features

- Scrapes advices from the Raad van State website for a specified year
- Analyzes the scraped advices and categorizes them based on standard dictum formulations
- Provides reasoning for the categorization
- Saves the scraped and analyzed data to CSV files

Certainly! Here's an updated version of the README.md file with additional information on the categories and the data being scraped:
markdown

Copy
# Raad van State Scraper and Analyzer

This repository contains a web scraper and analyzer for the Dutch Raad van State (Council of State) advices.

## Features

- Scrapes advices from the Raad van State website for a specified year
- Analyzes the scraped advices and categorizes them based on standard dictum formulations, see categories below
- Provides reasoning for the categorization
- Saves the scraped and analyzed data to CSV files

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

The scraped data is saved in a CSV file named `raad_van_state_adviezen_<year>.csv`.

## Installation

1. Clone the repository:
```
git clone https://github.com/your-username/raad-van-state-scraper.git
```
2. Install the required dependencies:
```
pip install -r requirements.txt
```
3. Set up the necessary environment variables:
- `REPLICATE_API_TOKEN`: Your Replicate API token for using the language model.

## Usage

1. Run the scraper to fetch advices for a specific year (default is 2025):
```
python src/scraper.py --year 2025
```
Optional arguments:
- `--test`: Run in test mode to scrape only 10 advices.
- `--year`: Specify the year to scrape advices for (e.g., 2024).

2. Run the analyzer to categorize the scraped advices:
```
python src/analyzer.py data/raad_van_state_adviezen_2025.csv
```
Optional arguments:
- `--test`: Run in test mode to analyze only 10 advices.
- `--start-row`: Start processing from a specific row number.

3. View the scraped and analyzed data in the `data/` directory.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvement, please open an issue or submit a pull request.

## License

This project is licensed under the GNU GPL v3
