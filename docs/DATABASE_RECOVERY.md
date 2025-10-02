# WHO CHOICE Price Database - Recovery Guide

## Overview

This document describes the successful recovery of the WHO CHOICE Price Database from the Excel file `5 WHO_CHOICE_Price_Database_2019_A3.xlsx`.

## What Was Done

### 1. Schema Analysis

The database schemas were reverse-engineered from the source code in `programme_costing_utilities/calculations.py`. All SQL queries were analyzed to determine:
- Table names
- Column names and types
- Relationships and usage patterns

Full schema documentation: **[database_schemas.md](./database_schemas.md)**

### 2. Excel Data Extraction

A Python script was created to extract data from the Excel file and populate a SQLite database:
- **Script**: `populate_database.py`
- **Output**: `./data/who_choice_price_database.db`

### 3. Database Population Results

| Table | Status | Rows | Source Sheet |
|-------|--------|------|--------------|
| administrative_divisions | ✓ Complete | 215 | 3.3 Administrative Divisions |
| healthcare_facilities | ✓ Complete | 215 | 3.4 Healthcare Facilities |
| costs_salaries | ✓ Complete | 915 | 4. Int salaries wide |
| costs_per_diems | ✓ Complete | 193 | 5. Travel Allowance & Per Diem |
| costs_transport | ✓ Complete | 9 | 6.1 Vehicles & Transport Costs |
| office_supplies_and_furniture | ✓ Complete | 49 | 10.Office Supp. & Furniture |
| distance_between_regions | ✓ Complete | 194 | 13. Distance between regions |
| economic_statistics | ✓ Complete | 542 | Migrated from CountryData.db |
| population | ✓ Complete | 30,200 | Migrated from CountryData.db |

## Usage

### Recreating the Database

```bash
# Run the population script
python3 populate_database.py
```

This will:
1. Create the `./data/` directory if needed
2. Delete any existing database
3. Create a new database with proper schemas
4. Populate all available tables from the Excel file

### Verification

```python
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('./data/who_choice_price_database.db')

# Example: Get salaries for Uganda
df = pd.read_sql_query("""
    SELECT * FROM costs_salaries
    WHERE ISO3 = 'UGA'
    ORDER BY ISCO_08_level DESC
""", conn)
print(df)
```

## Data Details

### Successfully Extracted Tables

#### 1. costs_salaries
- **Source**: Sheet "4. Int salaries wide"
- **Coverage**: 183 countries × 5 ISCO levels = 915 rows
- **Key fields**:
  - ISCO_08_level (1-5: Services, Support, Technicians, Professionals, Managers)
  - annual_salary (monthly salary × 12)
  - currency = "I$" (International dollars)
  - year = 2019

#### 2. costs_per_diems
- **Source**: Sheet "5. Travel Allowance & Per Diem"
- **Coverage**: 193 countries
- **Key fields**:
  - dsa_national (Capital city per diem in USD)
  - dsa_upper (Other upper cost areas)
  - dsa_lower (Other lower cost areas)
  - local_proportion = 0.2 (20% for local staff)

#### 3. costs_transport
- **Source**: Sheet "6.1 Vehicles & Transport Costs"
- **Coverage**: 9 vehicle models
- **Includes**: Toyota Hiace, Corolla sedan, Land Cruiser variants
- **Key fields**:
  - operating_cost_per_km (USD 2019)
  - consumption_litres_per_km

#### 4. office_supplies_and_furniture
- **Source**: Sheet "10.Office Supp. & Furniture"
- **Coverage**: 49 items (using 2022 prices)
- **Includes**: Computers, printers, furniture, stationery
- **Note**: Item names may have trailing spaces (as in original data)

#### 5. administrative_divisions
- **Source**: Sheet "3.3 Administrative Divisions"
- **Coverage**: 215 countries
- **Key fields**:
  - provincial_divisions (first sub-national level)
  - district_divisions (second sub-national level)

#### 6. healthcare_facilities
- **Source**: Sheet "3.4 Healthcare Facilities"
- **Coverage**: 215 countries
- **Facility types**: Regional hospitals, provincial hospitals, district hospitals, health centres, health posts

#### 7. distance_between_regions
- **Source**: Sheet "13. Distance between regions"
- **Coverage**: 194 countries
- **Percentile distances**: DDist10 through DDist100
- **Note**: Code references DDist95 for travel calculations

### Tables Migrated from External Data

#### 8. economic_statistics

**Status**: ✓ Migrated from CountryData.db

**Required data series**:
- PPP conversion factor, GDP (LCU per international $)
- GDP deflator (base year varies by country)
- GDP per capita, PPP (current international $)

**Data structure**:
- Wide format with columns for years 1960-2021
- Column naming: "1960 [YR1960]", "1961 [YR1961]", ..., "2021 [YR2021]"

**How to obtain**:
1. Download from [World Bank DataBank](https://databank.worldbank.org/)
2. Select indicators: GDP deflator, PPP conversion factor, GDP per capita PPP
3. Select all countries and years 1960-2021
4. Export and import into database

**Alternative**: Use World Bank API
```python
import wbdata
# Example code to fetch World Bank data
```

#### 9. population

**Status**: ✓ Migrated from CountryData.db

**Required data**:
- Years: 1950-2100
- By country (ISO3 code)
- Variants: At minimum "Median" variant
- Total population values

**How to obtain**:
1. Download from [UN Population Division](https://population.un.org/wpp/)
2. Select "World Population Prospects"
3. Download population estimates and projections
4. Import medium variant as "Median"

**Data structure**:
```sql
CREATE TABLE population (
    Iso3 TEXT,
    Time INTEGER,
    Variant TEXT,
    Value NUMERIC
)
```

## Key Mappings and Conventions

### Currency Codes
- "I$" = International dollars (PPP)
- "USD" or "USA" = US dollars (code uses both interchangeably)
- Other currencies use ISO3 country codes

### Personnel Cadre Levels (ISCO-08)
- Level 5: Managers
- Level 4: Professionals
- Level 3: Technicians
- Level 2: Support staff
- Level 1: Services

Mapping from role to cadre is in: `./data/personnel_cadre.json`

### Statistical Divisions
- National: Country-level
- Provincial: First sub-national division
- District: Second sub-national division

### Per Diem Levels
- dsa_national: Capital city / national level
- dsa_upper: Provincial level (other upper cost areas)
- dsa_lower: District level (other lower cost areas)
- Local staff receive 20% of international staff rate

## Data Quality Notes

1. **Office supplies**: Uses 2022 prices (most recent available)
2. **Transport costs**: Uses 2019 operating costs
3. **Salaries**: Monthly salaries converted to annual (×12)
4. **Missing values**: Some countries lack complete data across all tables
5. **Item naming**: Original Excel spacing preserved (e.g., "Computer   " with trailing spaces)

## Testing the Recreation

To verify your recreated database matches the expected structure:

```bash
# Run the test suite
python3 -m pytest tests/

# Or manually verify key lookups used in the code
python3 -c "
from programme_costing_utilities import calculations
import sqlite3

conn = sqlite3.connect('./data/who_choice_price_database.db')

# Test salary lookup for Uganda, cadre 2
salary, currency_info = calculations.serve_personnel_annual_salary('UGA', 2, conn)
print(f'Uganda cadre 2 salary: {salary} {currency_info}')

# Test per diem lookup for Uganda, district level
per_diem, currency_info = calculations.serve_per_diem('UGA', 'district', conn, False)
print(f'Uganda district per diem: {per_diem} {currency_info}')

conn.close()
"
```

## Migration from CountryData.db

The remaining tables (economic_statistics and population) were successfully migrated from `CountryData.db`:

### Migration Results

**economic_statistics** (542 rows)
- Migrated from: `PPP_Conversion_Factor` and `GDP_Deflator` tables
- Contains:
  - 271 rows of PPP conversion factors
  - 271 rows of GDP deflators
- Years: 1960-2021
- Countries: 271

**population** (30,200 rows)
- Migrated from: `Populations` table (with M49 to ISO3 conversion)
- Contains:
  - 200 countries
  - Years: 1950-2100
  - Variant: "Median"
  - Values: Total population summed across all age groups and both sexes
  - Note: Values are in thousands (e.g., 44,270 = 44.27 million)

### Migration Script

Run the migration using:
```bash
python3 migrate_country_data.py
```

This script:
1. Reads PPP conversion factors and GDP deflators from CountryData.db
2. Transforms them into the economic_statistics format with proper column naming
3. Reads population data, converts M49 codes to ISO3, and aggregates by country/year
4. Verifies the migration with test queries

## Next Steps

To validate the complete database:

1. **Test with sample inputs**
   - Run the main.py script with test JSON inputs
   - Verify calculations are working correctly

2. **Verify specific country data**
   - Check that currency conversions are accurate
   - Test population projections
   - Validate cost calculations

## Files Created

- `database_schemas.md` - Complete schema documentation
- `populate_database.py` - Database population script from Excel
- `migrate_country_data.py` - Migration script for external data
- `DATABASE_RECOVERY.md` - This file
- `./data/who_choice_price_database.db` - The complete SQLite database (all 9 tables populated)

## Support

For issues or questions about the database structure, refer to:
- Source code: `programme_costing_utilities/calculations.py`
- Runtime: `programme_costing_utilities/runtime.py`
- Original Excel: `5 WHO_CHOICE_Price_Database_2019_A3.xlsx`
