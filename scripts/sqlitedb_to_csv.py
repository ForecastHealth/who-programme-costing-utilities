import sqlite3
import pandas as pd

# replace this with your sqlite db path
db_filepath = './data/who_choice_price_database.db'
output_dir = './data/'

def main(db_path):
    # Connect to the database
    db = sqlite3.connect(db_path)

    # Get the cursor object
    cursor = db.cursor()

    # Get the list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table_name in tables:
        table_name = table_name[0]
        output_filepath = f'{output_dir}{table_name}.csv'
        print(f'Processing {table_name}...')

        table = pd.read_sql_query(f"SELECT * from {table_name}", db)
        table.to_csv(output_filepath, index_label='index')

    # Close the connection
    db.close()

if __name__ == "__main__":
    main(db_filepath)