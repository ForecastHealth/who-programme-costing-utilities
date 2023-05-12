import argparse
import json
import sqlite3
from programme_costing_utilities import runtime, components
DEFAULTS = {
    'country_iso3': "UGA",
    'start_year': 2023,
    'end_year': 2030,
    'discount_rate': 1,
    'currency': 'USD',
    'currency_year': 2018,
    'components': components.DEFAULT_COMPONENTS
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

def main():
    args = get_args()
    data = load_input_file(args.input)
    price_db, demography_db = load_database()
    results = runtime.run(data, price_db, demography_db)
    results.to_csv(args.output, index=False, encoding='utf-8')

if __name__ == '__main__':
    main()
