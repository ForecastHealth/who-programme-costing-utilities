"""
Script to populate the WHO CHOICE Price Database from the Excel file.

This script reads from: 5 WHO_CHOICE_Price_Database_2019_A3.xlsx
And creates: ./data/who_choice_price_database.db
"""

import sqlite3
import pandas as pd
import os
from pathlib import Path

EXCEL_FILE = './data/raw.xlsx'
DB_PATH = './data/who_choice_price_database.db'


def create_database_directory():
    """Create the data directory if it doesn't exist."""
    Path('./data').mkdir(exist_ok=True)


def create_tables(conn):
    """Create all database tables with proper schemas."""
    cursor = conn.cursor()

    # 1. Population table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS population (
            Iso3 TEXT,
            Time INTEGER,
            Variant TEXT,
            Value NUMERIC
        )
    """)

    # 2. Administrative divisions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS administrative_divisions (
            ISO3 TEXT PRIMARY KEY,
            provincial_divisions INTEGER,
            district_divisions INTEGER
        )
    """)

    # 3. Costs - Salaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS costs_salaries (
            ISO3 TEXT,
            ISCO_08_level INTEGER,
            annual_salary NUMERIC,
            currency TEXT,
            year INTEGER
        )
    """)

    # 4. Office supplies and furniture
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS office_supplies_and_furniture (
            item TEXT,
            price NUMERIC,
            currency TEXT,
            year INTEGER
        )
    """)

    # 5. Transport costs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS costs_transport (
            vehicle_model TEXT PRIMARY KEY,
            operating_cost_per_km NUMERIC,
            consumption_litres_per_km NUMERIC,
            currency TEXT,
            year INTEGER
        )
    """)

    # 6. Distance between regions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distance_between_regions (
            ISO3 TEXT PRIMARY KEY,
            DDist10 NUMERIC,
            DDist20 NUMERIC,
            DDist30 NUMERIC,
            DDist40 NUMERIC,
            DDist50 NUMERIC,
            DDist60 NUMERIC,
            DDist70 NUMERIC,
            DDist80 NUMERIC,
            DDist90 NUMERIC,
            DDist95 NUMERIC,
            DDist100 NUMERIC,
            size_km_sq NUMERIC
        )
    """)

    # 7. Per diems
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS costs_per_diems (
            ISO3 TEXT PRIMARY KEY,
            dsa_national NUMERIC,
            dsa_upper NUMERIC,
            dsa_lower NUMERIC,
            currency TEXT,
            year INTEGER,
            local_proportion NUMERIC
        )
    """)

    # 8. Economic statistics - wide format with year columns
    # This will be created dynamically based on the Excel data

    # 9. Healthcare facilities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS healthcare_facilities (
            ISO3 TEXT PRIMARY KEY,
            regional_hospitals INTEGER,
            provincial_hospitals INTEGER,
            district_hospitals INTEGER,
            health_centres INTEGER,
            health_posts INTEGER
        )
    """)

    conn.commit()
    print("✓ Database tables created")


def populate_administrative_divisions(conn):
    """Populate administrative_divisions table from sheet '3.3 Administrative Divisions'."""
    df = pd.read_excel(EXCEL_FILE, sheet_name='3.3 Administrative Divisions')

    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO administrative_divisions
            (ISO3, provincial_divisions, district_divisions)
            VALUES (?, ?, ?)
        """, (
            row['WHO Code'],
            row['Number of First Sub-National Divisions'],
            row['Number of Second Sub-National Divisions']
        ))

    conn.commit()
    print(f"✓ Populated administrative_divisions: {len(df)} rows")


def populate_healthcare_facilities(conn):
    """Populate healthcare_facilities table from sheet '3.4 Healthcare Facilities'."""
    df = pd.read_excel(EXCEL_FILE, sheet_name='3.4 Healthcare Facilities')

    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO healthcare_facilities
            (ISO3, regional_hospitals, provincial_hospitals, district_hospitals,
             health_centres, health_posts)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row['WHO Code'],
            int(row['Regional Hospitals, Total Number']) if pd.notna(row['Regional Hospitals, Total Number']) else 0,
            int(row['Provincial Hospitals, Total Number']) if pd.notna(row['Provincial Hospitals, Total Number']) else 0,
            int(row['District Hospitals,\nTotal Number']) if pd.notna(row['District Hospitals,\nTotal Number']) else 0,
            int(row['Health Centres, Total Number']) if pd.notna(row['Health Centres, Total Number']) else 0,
            int(row['Health Posts, Total Number']) if pd.notna(row['Health Posts, Total Number']) else 0
        ))

    conn.commit()
    print(f"✓ Populated healthcare_facilities: {len(df)} rows")


def populate_salaries(conn):
    """Populate costs_salaries table from sheet '4. Int salaries wide'."""
    # Read the sheet with no header
    df = pd.read_excel(EXCEL_FILE, sheet_name='4. Int salaries wide', header=None)

    # Row 2 contains the headers
    # Column 1 = ISO3
    # Columns 2-6 are METHOD 1: [5 Managers, 4 Professionals, 3 Technicians, 2 Support, 1 Services]
    # Values are monthly salaries in international dollars (I$) for 2019

    cursor = conn.cursor()
    count = 0

    # Data starts at row 3
    for idx in range(3, len(df)):
        row = df.iloc[idx]
        iso3 = row[1]

        if pd.isna(iso3):
            continue

        # Map columns to ISCO levels and convert monthly to annual
        isco_levels = {
            5: row[2] * 12 if pd.notna(row[2]) else None,  # Managers
            4: row[3] * 12 if pd.notna(row[3]) else None,  # Professionals
            3: row[4] * 12 if pd.notna(row[4]) else None,  # Technicians
            2: row[5] * 12 if pd.notna(row[5]) else None,  # Support
            1: row[6] * 12 if pd.notna(row[6]) else None   # Services
        }

        for isco_level, annual_salary in isco_levels.items():
            if annual_salary is not None:
                cursor.execute("""
                    INSERT OR REPLACE INTO costs_salaries
                    (ISO3, ISCO_08_level, annual_salary, currency, year)
                    VALUES (?, ?, ?, ?, ?)
                """, (iso3, isco_level, annual_salary, 'I$', 2019))
                count += 1

    conn.commit()
    print(f"✓ Populated costs_salaries: {count} rows")


def populate_per_diems(conn):
    """Populate costs_per_diems table from sheet '5. Travel Allowance & Per Diem'."""
    # Read with no header
    df = pd.read_excel(EXCEL_FILE, sheet_name='5. Travel Allowance & Per Diem', header=None)

    # Extract local proportion from cell B1 (row 0, col 2)
    local_proportion = df.iloc[0, 2] if pd.notna(df.iloc[0, 2]) else 0.2

    # Row 3 contains headers
    # Column 1 = ISO3
    # Column 2 = DSA Capital City (dsa_national)
    # Column 5 = DSA Other Lower Cost (dsa_lower)
    # Column 8 = DSA Other Upper Cost (dsa_upper)
    # Currency is USD, year is 2019

    cursor = conn.cursor()

    # Data starts at row 4
    for idx in range(4, len(df)):
        row = df.iloc[idx]
        iso3 = row[1]

        if pd.isna(iso3):
            continue

        dsa_national = row[2] if pd.notna(row[2]) else None
        dsa_lower = row[5] if pd.notna(row[5]) else None
        dsa_upper = row[8] if pd.notna(row[8]) else None

        if dsa_national or dsa_lower or dsa_upper:
            cursor.execute("""
                INSERT OR REPLACE INTO costs_per_diems
                (ISO3, dsa_national, dsa_upper, dsa_lower, currency, year, local_proportion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (iso3, dsa_national, dsa_upper, dsa_lower, 'USD', 2019, local_proportion))

    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM costs_per_diems").fetchone()[0]
    print(f"✓ Populated costs_per_diems: {count} rows (local_proportion={local_proportion})")


def populate_transport_costs(conn):
    """Populate costs_transport table from sheet '6.1 Vehicles & Transport Costs'."""
    df = pd.read_excel(EXCEL_FILE, sheet_name='6.1 Vehicles & Transport Costs')

    cursor = conn.cursor()
    for _, row in df.iterrows():
        if pd.notna(row['Vehicle Model']):
            cursor.execute("""
                INSERT OR REPLACE INTO costs_transport
                (vehicle_model, operating_cost_per_km, consumption_litres_per_km,
                 currency, year)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row['Vehicle Model'],
                row['Operating cost per km (2019)'] if pd.notna(row['Operating cost per km (2019)']) else None,
                row['Consumption\n (l per km)'] if pd.notna(row['Consumption\n (l per km)']) else None,
                'USD',
                2019
            ))

    conn.commit()
    print(f"✓ Populated costs_transport: {len(df)} rows")


def populate_office_supplies(conn):
    """Populate office_supplies_and_furniture table from sheet '10.Office Supp. & Furniture'."""
    df = pd.read_excel(EXCEL_FILE, sheet_name='10.Office Supp. & Furniture')

    cursor = conn.cursor()
    for _, row in df.iterrows():
        if pd.notna(row['Item']):
            # Using 2022 prices as they're most recent
            price = row['Price\n(USD 2022)\nOne Unit'] if pd.notna(row['Price\n(USD 2022)\nOne Unit']) else None
            if price is not None:
                cursor.execute("""
                    INSERT OR REPLACE INTO office_supplies_and_furniture
                    (item, price, currency, year)
                    VALUES (?, ?, ?, ?)
                """, (
                    row['Item'],
                    price,
                    'USD',
                    2022
                ))

    conn.commit()
    print(f"✓ Populated office_supplies_and_furniture: {len(df)} rows")


def populate_distance_between_regions(conn):
    """Populate distance_between_regions table from sheet '13. Distance between regions'."""
    df = pd.read_excel(EXCEL_FILE, sheet_name='13. Distance between regions')

    cursor = conn.cursor()
    for _, row in df.iterrows():
        if pd.notna(row['Unnamed: 1']):  # ISO3 code column
            cursor.execute("""
                INSERT OR REPLACE INTO distance_between_regions
                (ISO3, DDist10, DDist20, DDist30, DDist40, DDist50,
                 DDist60, DDist70, DDist80, DDist90, DDist95, DDist100, size_km_sq)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['Unnamed: 1'],
                row['DDist10'], row['DDist20'], row['DDist30'], row['DDist40'],
                row['DDist50'], row['DDist60'], row['DDist70'], row['DDist80'],
                row['DDist90'], row['DDist95'], row['DDist100'],
                row.get('Size') if pd.notna(row.get('Size')) else None
            ))

    conn.commit()
    print(f"✓ Populated distance_between_regions: {len(df)} rows")


def populate_economic_statistics(conn):
    """Populate economic_statistics table from sheet '3.2 Prices and Deflators'."""
    print("⚠ Economic statistics table - requires World Bank data")
    print("  This appears to be World Bank economic data with columns for each year 1960-2021")
    print("  The Excel sheet '3.2 Prices and Deflators' may not have all the data")
    print("  Original database likely sourced this from World Bank API or downloads")


def populate_population(conn):
    """Populate population table."""
    print("⚠ Population table - requires UN population data")
    print("  Population data (1950-2100) not found in Excel file")
    print("  Likely sourced from UN Population Division separately")


def main():
    """Main function to populate the database."""
    print("="*80)
    print("WHO CHOICE Price Database - Population Script")
    print("="*80)
    print()

    # Create data directory
    create_database_directory()

    # Remove old database if exists
    if os.path.exists(DB_PATH):
        print(f"Removing existing database: {DB_PATH}")
        os.remove(DB_PATH)

    # Create new database
    conn = sqlite3.connect(DB_PATH)
    print(f"Created new database: {DB_PATH}")
    print()

    try:
        # Create tables
        create_tables(conn)
        print()

        # Populate tables
        print("Populating tables from Excel file...")
        print()
        populate_administrative_divisions(conn)
        populate_healthcare_facilities(conn)
        populate_salaries(conn)
        populate_per_diems(conn)
        populate_transport_costs(conn)
        populate_office_supplies(conn)
        populate_distance_between_regions(conn)

        # These require external data sources
        print()
        print("Tables requiring external data sources:")
        print()
        populate_economic_statistics(conn)
        populate_population(conn)

        print()
        print("="*80)
        print("Database population complete")
        print("="*80)
        print()
        print("Summary:")
        print("✓ Administrative divisions")
        print("✓ Healthcare facilities")
        print("✓ Salaries (ISCO-08 levels)")
        print("✓ Per diems (DSA rates)")
        print("✓ Transport costs")
        print("✓ Office supplies and furniture")
        print("✓ Distance between regions")
        print()
        print("External data needed:")
        print("⚠ Economic statistics (World Bank data: GDP deflators, PPP conversion factors)")
        print("⚠ Population (UN population data 1950-2100)")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
