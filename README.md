# Raad van State Scraper and Analyzer

This repository contains a web scraper and analyzer for the Dutch Raad van State (Council of State) advices.

## Features

- Scrapes advices from the Raad van State website for a specified year
- Analyzes the scraped advices and categorizes them based on standard dictum formulations
- Provides reasoning for the categorization
- Saves the scraped and analyzed data to CSV files

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
python src/scraper2.py --year 2025
```
Optional arguments:
- `--test`: Run in test mode to scrape only 10 advices.
- `--year`: Specify the year to scrape advices for (e.g., 2024).

2. Run the analyzer to categorize the scraped advices:
```
python src/analyzer2.py data/raad_van_state_adviezen_2025.csv
```
Optional arguments:
- `--test`: Run in test mode to analyze only 10 advices.
- `--start-row`: Start processing from a specific row number.

3. View the scraped and analyzed data in the `data/` directory.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvement, please open an issue or submit a pull request.

## License

This project is licensed under the GNU GPL v3
