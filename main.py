import argparse
import json
import sqlite3
from programme_costing_utilities import runtime

with open("./templates/personnel.json", "r", encoding="utf-8") as file:
    default_personnel = json.load(file)
with open("./templates/meetings.json", "r", encoding="utf-8") as file:
    default_meetings = json.load(file)
with open("./templates/media.json", "r", encoding="utf-8") as file:
    default_media = json.load(file)

DEFAULTS = {
    "country": "UGA",
    "start_year": 2020,
    "end_year": 2020,
    "discount_rate": 1,
    "desired_currency": "USD",
    "desired_year": 2018,
    "components": {
        "personnel": default_personnel,
        "meetings": default_meetings,
        "media": default_media
    }
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
    conn = sqlite3.connect('./data/who_choice_price_database.db')
    return conn

def main():
    args = get_args()
    data = load_input_file(args.input)
    conn = load_database()
    results = runtime.run(data, conn)
    results.to_csv(args.output, index=False, encoding='utf-8')

if __name__ == '__main__':
    main()
