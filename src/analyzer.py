#!/usr/bin/env python3
import pandas as pd
import replicate
import time
import logging
from typing import Optional, Tuple, Dict
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdviceAnalyzer:
    def __init__(self, input_file: str, test_mode: bool = False):
        self.input_file = input_file
        self.test_mode = test_mode
        self.model = "meta/meta-llama-3.1-405b-instruct"

        # Check for REPLICATE_API_TOKEN
        if 'REPLICATE_API_TOKEN' not in os.environ:
            raise ValueError(
                "REPLICATE_API_TOKEN not found. Please set it with:\n"
                "export REPLICATE_API_TOKEN='your_token_here'\n"
                "or on Windows:\n"
                "set REPLICATE_API_TOKEN=your_token_here"
            )

    def truncate_text(self, text: str, max_chars: int = 6000) -> str:
        """Truncate text intelligently by looking for the dictum near the end"""
        if not text or len(text) <= max_chars:
            return text

        # First check for standard dictum formulation
        dictum_start = "De Afdeling advisering van de Raad van State heeft"
        if dictum_start in text:
            # Get the last occurrence as it's most likely the actual dictum
            start_pos = text.rfind(dictum_start)
            if start_pos >= 0:
                # Include enough text after to capture the full dictum
                end_pos = min(start_pos + 500, len(text))
                return text[max(0, start_pos - 100):end_pos]  # Include some context before

        # If no standard dictum found, look for formal endings
        endings = [
            "Met de Koning",
            "De vice-president,",
            "De Afdeling advisering van de Raad van State",
            "De Voorzitter van de Afdeling advisering",
        ]

        # Find the last occurrence of any ending
        last_end_pos = -1
        found_ending = None

        for ending in endings:
            pos = text.rfind(ending)  # Use rfind to get the last occurrence
            if pos > last_end_pos:
                last_end_pos = pos
                found_ending = ending

        if last_end_pos >= 0:
            # Include text before and after the ending
            start_pos = max(0, last_end_pos - 3000)  # Take substantial text before
            end_pos = min(last_end_pos + len(found_ending) + 250, len(text))  # And 250 chars after
            return text[start_pos:end_pos]

        # If no endings found, take the last part of the text
        if len(text) > max_chars:
            return "..." + text[-max_chars:]

        return text

    def create_prompt(self, content: str) -> str:
        return f"""Je bent een expert in het analyseren van adviezen van de Raad van State. Analyseer het dictum (eindoordeel) in onderstaand advies.

STAP 1: Zoek eerst naar een van de vier standaard formuleringen:

A) "De Afdeling advisering van de Raad van State heeft geen opmerkingen bij het voorstel en adviseert het voorstel bij de Tweede Kamer der Staten-Generaal in te dienen."

B) "De Afdeling advisering van de Raad van State heeft een aantal opmerkingen bij het voorstel en adviseert daarmee rekening te houden voordat het voorstel bij de Tweede Kamer der Staten-Generaal wordt ingediend."

C) "De Afdeling advisering van de Raad van State heeft een aantal bezwaren bij het voorstel en adviseert het voorstel niet bij de Tweede Kamer der Staten-Generaal in te dienen, tenzij het is aangepast."

D) "De Afdeling advisering van de Raad van State heeft ernstige bezwaren tegen het voorstel en adviseert het niet bij de Tweede Kamer der Staten-Generaal in te dienen."

STAP 2: Als je GEEN van bovenstaande formuleringen vindt, bepaal dan of het een advies in oude stijl is:

E) Oude stijl - positief: Het advies bevat geen of slechts enkele opmerkingen EN adviseert (impliciet of expliciet) om het voorstel naar de Tweede Kamer te sturen

F) Oude stijl - kritisch: Het advies adviseert tot aanpassing van het voorstel of de toelichting EN/OF adviseert om het stuk nog niet naar de Tweede Kamer te sturen

G) Alleen gebruiken als het echt onduidelijk is of als er geen eindoordeel te vinden is

Geef je antwoord in JSON format:
{{
    "category": "X",  // Één letter: A, B, C, D, E, F of G
    "confidence": 0.0, // Getal tussen 0 en 1
    "reasoning": "" // Korte toelichting waarom je voor deze categorie kiest
}}

Geef ALLEEN het JSON object terug, geen andere tekst.

Advies:
{content}"""

    def check_standard_dictum(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Check for standard dictum formulations using regex"""
        import re

        # Helper function to make spaces flexible
        def flex(s: str) -> str:
            """Make spaces optional in a pattern string"""
            return r'\s*'.join(s.split())

        # Common starting phrase with flexible spaces
        start = flex("De Afdeling advisering van de Raad van State heeft")

        # Parts that can vary in multiple patterns
        proposal_vars = r'(het\s+voorstel|de\s+ontwerpbesluiten|het\s+ontwerpbesluit)'
        proposal_ref = r'(het\s+voorstel|deze|het)'
        bij_over = r'(bij|over)'
        besluit_vars = r'(het|een)\s+besluit'

        # Define patterns with variations
        patterns = {
            'A': [
                # Standard Tweede Kamer variant
                rf'{start}\s+geen\s+opmerkingen\s+{bij_over}\s+{proposal_vars}\s+en\s+adviseert\s+{proposal_ref}\s+bij\s+de\s+Tweede\s+Kamer\s+der\s+Staten-Generaal\s+in\s+te\s+dienen',
                # Besluit variant
                rf'{start}\s+geen\s+opmerkingen\s+{bij_over}\s+{proposal_vars}\s+en\s+adviseert\s+{besluit_vars}\s+te\s+nemen'
            ],

            'B': [
                # Standard Tweede Kamer variant
                rf'{start}\s+een\s+aantal\s+opmerkingen\s+{bij_over}\s+{proposal_vars}\s+en\s+adviseert\s+daarmee\s+rekening\s+te\s+houden\s+voordat\s+{proposal_ref}\s+bij\s+de\s+Tweede\s+Kamer\s+der\s+Staten-Generaal\s+(wordt|worden)\s+ingediend',
                # Besluit variant
                rf'{start}\s+een\s+aantal\s+opmerkingen\s+{bij_over}\s+{proposal_vars}\s+en\s+adviseert\s+daarmee\s+rekening\s+te\s+houden\s+voordat\s+{besluit_vars}\s+(wordt|worden)\s+genomen'
            ],

            'C': [
                # Standard Tweede Kamer variant
                rf'{start}\s+(een\s+aantal\s+)?bezwaren\s+{bij_over}\s+{proposal_vars}\s+en\s+adviseert\s+{proposal_ref}\s+niet\s+bij\s+de\s+Tweede\s+Kamer\s+der\s+Staten-Generaal\s+in\s+te\s+dienen,\s*tenzij\s+(het|deze)\s+(is|zijn)\s+aangepast',
                # Besluit variant
                rf'{start}\s+(een\s+aantal\s+)?bezwaren\s+{bij_over}\s+{proposal_vars}\s+en\s+adviseert\s+{besluit_vars}\s+niet\s+te\s+nemen,\s*tenzij\s+(het|deze)\s+(is|zijn)\s+aangepast'
            ],

            'D': [
                # Standard Tweede Kamer variant
                rf'{start}\s+ernstige\s+bezwaren\s+tegen\s+{proposal_vars}\s+en\s+adviseert\s+{proposal_ref}\s+niet\s+bij\s+de\s+Tweede\s+Kamer\s+der\s+Staten-Generaal\s+in\s+te\s+dienen',
                # Besluit variant
                rf'{start}\s+ernstige\s+bezwaren\s+tegen\s+{proposal_vars}\s+en\s+adviseert\s+{besluit_vars}\s+niet\s+te\s+nemen'
            ]
        }

        # Normalize spaces in input text
        text = ' '.join(text.split())

        # Check each pattern
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                # Add word boundaries where appropriate
                pattern = rf"\b{pattern}\b"
                matches = re.search(pattern, text, re.IGNORECASE)
                if matches:
                    matched_text = matches.group(0)
                    return category, f"Found standard dictum category {category}. Matched text: {matched_text}"

        return None, None

    def analyze_advice(self, content: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Analyze a single advice text and return the category, error, and reasoning"""
        if not content or pd.isna(content):
            return "G", "Empty or NaN content", None

        try:
            # First try to find standard dictum using regex
            category, reasoning = self.check_standard_dictum(content)
            if category:
                # If we find a standard pattern, return it with no error and the regex match explanation
                logger.info(f"Found standard pattern {category} - skipping LLM")
                return category, None, f"Regex match: {reasoning}"

            # If no standard dictum found, use language model
            logger.info("No standard pattern found, using LLM")
            truncated_content = self.truncate_text(content)

            input_data = {
                "prompt": self.create_prompt(truncated_content),
                "max_tokens": 1024,
                "temperature": 0.1
            }

            result = ""
            for event in replicate.stream(
                self.model,
                input=input_data
            ):
                result += str(event)

            # Parse JSON response
            try:
                result = result.strip()
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result[json_start:json_end]
                    parsed = json.loads(json_str)

                    category = parsed.get('category', 'G')
                    confidence = parsed.get('confidence', 0.0)
                    reasoning = parsed.get('reasoning', '')

                    if category not in "ABCDEFG":
                        return "G", f"Invalid category in response: {category}", None

                    if confidence < 0.7:  # If model is not confident enough
                        return category, f"Low confidence: {confidence}", reasoning

                    return category, None, reasoning
                else:
                    return "G", f"Could not find JSON in response: {result}", None

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {result}")
                return "G", f"Invalid JSON response: {str(e)}", None

        except Exception as e:
            logger.error(f"Error analyzing advice: {str(e)}")
            return "G", str(e), None

    def save_single_result(self, row_data: dict) -> None:
        """Save a single result immediately after processing"""
        try:
            # Create or append to results file
            output_file = self.input_file.replace('.csv', '_analyzed.csv')

            # If file doesn't exist, create it with headers
            if not os.path.exists(output_file):
                pd.DataFrame([row_data], columns=['url', 'reference', 'advice_type', 'category', 'error', 'reasoning']).to_csv(output_file, index=False)
            else:
                # Append without headers
                pd.DataFrame([row_data]).to_csv(output_file, mode='a', header=False, index=False)

            logger.info(f"Saved result for {row_data['reference']}")
        except Exception as e:
            logger.error(f"Error saving single result: {str(e)}")

    def get_completed_references(self) -> set:
        """Get set of references that have already been processed"""
        output_file = self.input_file.replace('.csv', '_analyzed.csv')
        if os.path.exists(output_file):
            try:
                completed_df = pd.read_csv(output_file)
                return set(completed_df['reference'].astype(str))
            except Exception as e:
                logger.error(f"Error reading completed results: {str(e)}")
        return set()

    def process_file(self, start_row: int = 0) -> None:
        """Process the entire CSV file"""
        try:
            # Read input CSV
            df = pd.read_csv(self.input_file)
            logger.info(f"Loaded {len(df)} rows from {self.input_file}")

            # Get already processed references
            completed_refs = self.get_completed_references()

            # If in test mode, only take first 10 rows
            if self.test_mode:
                df = df.head(10)
                logger.info("Test mode: processing first 10 rows only")

            # Process each row
            for idx, row in df.iterrows():
                # Skip rows before start_row
                if idx < start_row:
                    continue

                # Skip already processed rows
                if str(row['reference']) in completed_refs:
                    logger.info(f"Skipping already processed row {idx + 1}: {row['reference']}")
                    continue

                logger.info(f"Processing advice {idx + 1}/{len(df)} - {row['reference']}")
                try:
                    category, error, reasoning = self.analyze_advice(row['content'])

                    # Create result dictionary
                    result = {
                        'url': row['url'],
                        'reference': row['reference'],
                        'advice_type': row.get('advice_type', None),  # Add advice_type from original row
                        'category': category,
                        'error': error,
                        'reasoning': reasoning
                    }

                    # Save immediately
                    self.save_single_result(result)

                except Exception as e:
                    logger.error(f"Error processing row {idx + 1}: {str(e)}")
                    result = {
                        'url': row['url'],
                        'reference': row['reference'],
                        'category': 'G',
                        'error': str(e),
                        'reasoning': None
                    }
                    self.save_single_result(result)

                # Add delay to respect rate limits
                time.sleep(2)

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze Raad van State advices')
    parser.add_argument('input_file', help='Input CSV file with advices')
    parser.add_argument('--test', action='store_true', help='Run in test mode (only 10 advices)')
    parser.add_argument('--start-row', type=int, default=0, help='Start processing from this row number')
    args = parser.parse_args()

    analyzer = AdviceAnalyzer(args.input_file, test_mode=args.test)

    try:
        analyzer.process_file(start_row=args.start_row)
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user. Progress has been saved.")

if __name__ == "__main__":
    main()
