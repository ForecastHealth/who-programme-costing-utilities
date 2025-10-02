"""
Script to migrate economic_statistics and population tables from CountryData.db
to who_choice_price_database.db with the correct schemas.
"""

import sqlite3
import pandas as pd
from pathlib import Path

SOURCE_DB = './CountryData.db'
TARGET_DB = './data/who_choice_price_database.db'


def migrate_economic_statistics(source_conn, target_conn):
    """
    Migrate PPP_Conversion_Factor and GDP_Deflator tables into economic_statistics.

    The target schema expects:
    - "Country Code" column
    - "Series Name" column
    - Year columns formatted as "1960 [YR1960]", "1961 [YR1961]", etc.
    """
    print("Migrating economic statistics...")

    # Read PPP conversion factors
    ppp_df = pd.read_sql_query("SELECT * FROM PPP_Conversion_Factor", source_conn)

    # Read GDP deflators
    gdp_deflator_df = pd.read_sql_query("SELECT * FROM GDP_Deflator", source_conn)

    # Create the economic_statistics table with proper column names
    # Year columns need to be in format "YYYY [YRYYYY]"
    year_columns = []
    for year in range(1960, 2022):
        year_columns.append(f'"{year} [YR{year}]" REAL')

    year_columns_sql = ', '.join(year_columns)

    target_cursor = target_conn.cursor()
    target_cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS economic_statistics (
            "Country Code" TEXT,
            "Series Name" TEXT,
            {year_columns_sql}
        )
    """)

    # Clear any existing data
    target_cursor.execute("DELETE FROM economic_statistics")

    # Insert PPP conversion factors
    series_name_ppp = "PPP conversion factor, GDP (LCU per international $)"
    for _, row in ppp_df.iterrows():
        country_code = row['Country Code']

        # Build the value list for years 1960-2021
        values = [country_code, series_name_ppp]
        for year in range(1960, 2022):
            values.append(row[str(year)] if pd.notna(row[str(year)]) else None)

        # Create placeholders
        placeholders = ', '.join(['?' for _ in range(len(values))])

        target_cursor.execute(f"""
            INSERT INTO economic_statistics VALUES ({placeholders})
        """, values)

    ppp_count = len(ppp_df)
    print(f"  ✓ Inserted {ppp_count} rows for PPP conversion factors")

    # Insert GDP deflators
    series_name_deflator = "GDP deflator (base year varies by country)"
    for _, row in gdp_deflator_df.iterrows():
        country_code = row['Country Code']

        # Build the value list for years 1960-2021
        values = [country_code, series_name_deflator]
        for year in range(1960, 2022):
            values.append(row[str(year)] if pd.notna(row[str(year)]) else None)

        # Create placeholders
        placeholders = ', '.join(['?' for _ in range(len(values))])

        target_cursor.execute(f"""
            INSERT INTO economic_statistics VALUES ({placeholders})
        """, values)

    deflator_count = len(gdp_deflator_df)
    print(f"  ✓ Inserted {deflator_count} rows for GDP deflators")

    target_conn.commit()
    print(f"✓ Economic statistics migration complete: {ppp_count + deflator_count} total rows")


def migrate_population(source_conn, target_conn):
    """
    Migrate Populations table to population table.

    The target schema expects:
    - Iso3 (TEXT) - ISO3 country code
    - Time (INTEGER) - Year
    - Variant (TEXT) - e.g., "Median"
    - Value (NUMERIC) - Total population

    Source has:
    - M49 (country code)
    - SEX (0=Male, 1=Female)
    - YEAR
    - N0-N100 (age groups 0-100)

    We need to:
    1. Sum all age groups to get total population per country/sex/year
    2. Sum both sexes to get total population
    3. Convert M49 to ISO3
    4. Set Variant to "Median"
    """
    print("Migrating population data...")

    # Get M49 to ISO3 mapping
    metadata_df = pd.read_sql_query("SELECT M49, ISO3 FROM Metadata WHERE ISO3 IS NOT NULL", source_conn)
    m49_to_iso3 = dict(zip(metadata_df['M49'], metadata_df['ISO3']))

    # Read populations
    # We need to sum across all age columns (N0-N100)
    populations_df = pd.read_sql_query("SELECT * FROM Populations", source_conn)

    # Get age columns (N0 through N100)
    age_columns = [f'N{i}' for i in range(101)]

    # Calculate total population by summing all age groups
    populations_df['total_population'] = populations_df[age_columns].sum(axis=1)

    # Group by M49 and YEAR, summing across both sexes
    grouped = populations_df.groupby(['M49', 'YEAR'])['total_population'].sum().reset_index()

    # Convert to thousands (since the original values appear to be in thousands based on the sample)
    # Actually, looking at the values, they seem to already be in the right scale

    # Create target table
    target_cursor = target_conn.cursor()
    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS population (
            Iso3 TEXT,
            Time INTEGER,
            Variant TEXT,
            Value NUMERIC
        )
    """)

    # Clear any existing data
    target_cursor.execute("DELETE FROM population")

    # Insert data
    inserted_count = 0
    skipped_count = 0

    for _, row in grouped.iterrows():
        m49 = row['M49']
        year = int(row['YEAR'])
        population = row['total_population']

        # Convert M49 to ISO3
        if m49 in m49_to_iso3:
            iso3 = m49_to_iso3[m49]

            target_cursor.execute("""
                INSERT INTO population (Iso3, Time, Variant, Value)
                VALUES (?, ?, ?, ?)
            """, (iso3, year, "Median", population))

            inserted_count += 1
        else:
            skipped_count += 1

    target_conn.commit()
    print(f"  ✓ Inserted {inserted_count} population records")
    if skipped_count > 0:
        print(f"  ⚠ Skipped {skipped_count} records (no ISO3 mapping)")

    print(f"✓ Population migration complete")


def verify_migration(conn):
    """Verify that the migrated data is accessible using the expected queries."""
    print("\nVerifying migrated data...")
    print("="*80)

    cursor = conn.cursor()

    # Test 1: Population query (from serve_population)
    print("\n1. Testing population query (Uganda, 2019):")
    cursor.execute("""
        SELECT Value
        FROM population
        WHERE Iso3 = 'UGA'
        AND Time = 2019
        AND Variant = 'Median'
    """)
    result = cursor.fetchone()
    if result:
        print(f"   ✓ Uganda 2019 population: {result[0]:,.0f}")
    else:
        print("   ✗ No result found")

    # Test 2: PPP conversion factor query (from rebase_currency)
    print("\n2. Testing PPP conversion factor (USA, 2019):")
    cursor.execute("""
        SELECT "2019 [YR2019]"
        FROM economic_statistics
        WHERE "Country Code" = 'USA'
        AND "Series Name" = 'PPP conversion factor, GDP (LCU per international $)'
    """)
    result = cursor.fetchone()
    if result:
        print(f"   ✓ USA 2019 PPP factor: {result[0]}")
    else:
        print("   ✗ No result found")

    # Test 3: GDP deflator query
    print("\n3. Testing GDP deflator (Uganda, 2018-2019):")
    cursor.execute("""
        SELECT "2018 [YR2018]", "2019 [YR2019]"
        FROM economic_statistics
        WHERE "Country Code" = 'UGA'
        AND "Series Name" = 'GDP deflator (base year varies by country)'
    """)
    result = cursor.fetchone()
    if result:
        print(f"   ✓ Uganda GDP deflators: 2018={result[0]}, 2019={result[1]}")
    else:
        print("   ✗ No result found")

    # Test 4: Count records
    print("\n4. Record counts:")
    cursor.execute("SELECT COUNT(*) FROM economic_statistics")
    econ_count = cursor.fetchone()[0]
    print(f"   ✓ economic_statistics: {econ_count} rows")

    cursor.execute("SELECT COUNT(*) FROM population")
    pop_count = cursor.fetchone()[0]
    print(f"   ✓ population: {pop_count} rows")

    cursor.execute("SELECT COUNT(DISTINCT Iso3) FROM population")
    country_count = cursor.fetchone()[0]
    print(f"   ✓ population countries: {country_count}")

    cursor.execute("SELECT MIN(Time), MAX(Time) FROM population")
    year_range = cursor.fetchone()
    print(f"   ✓ population year range: {year_range[0]}-{year_range[1]}")

    print("\n" + "="*80)
    print("Verification complete!")


def main():
    """Main migration function."""
    print("="*80)
    print("Country Data Migration Script")
    print("="*80)
    print(f"Source: {SOURCE_DB}")
    print(f"Target: {TARGET_DB}")
    print()

    # Check if source database exists
    if not Path(SOURCE_DB).exists():
        print(f"✗ Error: Source database not found: {SOURCE_DB}")
        return

    # Check if target database exists
    if not Path(TARGET_DB).exists():
        print(f"✗ Error: Target database not found: {TARGET_DB}")
        print("Please run populate_database.py first to create the target database.")
        return

    # Connect to databases
    source_conn = sqlite3.connect(SOURCE_DB)
    target_conn = sqlite3.connect(TARGET_DB)

    try:
        # Migrate economic statistics
        migrate_economic_statistics(source_conn, target_conn)
        print()

        # Migrate population
        migrate_population(source_conn, target_conn)
        print()

        # Verify migration
        verify_migration(target_conn)

        print()
        print("="*80)
        print("Migration complete!")
        print("="*80)

    finally:
        source_conn.close()
        target_conn.close()


if __name__ == '__main__':
    main()
