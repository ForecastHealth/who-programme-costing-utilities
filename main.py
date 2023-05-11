import argparse
import json
import sqlite3
import pandas as pd
DEFAULT_MODULES = []
DEFAULTS = {
    'start_year': 2023,
    'end_year': 2030,
    'discount_rate': 1,
    'currency': 'USD',
    'currency_year': 2018,
    'modules': DEFAULT_MODULES
}

def get_args():
    parser = argparse.ArgumentParser(description='A utility for producing modular programme costs.')
    parser.add_argument('-i', '--input', required=True, help='Input JSON file')
    parser.add_argument('-o', '--output', required=True, help='Output CSV file')
    return parser.parse_args()

def load_input_file(input_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return {**DEFAULTS, **data}

def load_database():
    conn1 = sqlite3.connect('./data/who_choice_price_database.db')
    conn2 = sqlite3.connect('./data/undpp_wpp.db')
    return conn1, conn2

def calculate_programme_costs(data, conn1, conn2):
    # Logic for calculating programme costs goes here. 
    # This might include querying the databases, performing calculations, etc.
    # As the details of these calculations are not provided, I'll return an empty DataFrame for now.
    return pd.DataFrame()

def main():
    args = get_args()
    data = load_input_file(args.input)
    conn1, conn2 = load_database()
    results = calculate_programme_costs(data, conn1, conn2)
    results.to_csv(args.output, index=False, encoding='utf-8')

if __name__ == '__main__':
    main()
