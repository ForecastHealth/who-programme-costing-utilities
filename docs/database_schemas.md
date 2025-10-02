# WHO CHOICE Price Database Schemas

This document describes the database schemas for the WHO CHOICE Price Database, which was stored at `./data/who_choice_price_database.db`.

## Database Tables

### 1. population

Stores population data by country, year, and variant.

```sql
Columns:
- Iso3 (TEXT) - ISO3 country code
- Time (INTEGER) - Year
- Variant (TEXT) - Population variant (e.g., "Median")
- Value (NUMERIC) - Population value
```

**Referenced in**: `serve_population()` - calculations.py:736

---

### 2. administrative_divisions

Stores the number of administrative divisions (provincial and district) per country.

```sql
Columns:
- ISO3 (TEXT) - ISO3 country code
- [Column 1] (INTEGER) - Number of provincial divisions
- [Column 2] (INTEGER) - Number of district divisions
```

**Referenced in**: `serve_number_of_divisions()` - calculations.py:774

---

### 3. costs_salaries

Stores annual salary information by country and personnel cadre level.

```sql
Columns:
- ISO3 (TEXT) - ISO3 country code
- ISCO_08_level (INTEGER) - Personnel cadre level (1-5, based on ISCO-08 classification)
- annual_salary (NUMERIC) - Annual salary amount
- currency (TEXT) - Currency code
- year (INTEGER) - Year of the cost data
```

**Referenced in**: `serve_personnel_annual_salary()` - calculations.py:853

---

### 4. office_supplies_and_furniture

Stores pricing for office supplies and furniture items.

```sql
Columns:
- item (TEXT) - Item name (e.g., "Computer   ", "Multifunciton Photocopier, Fax, Printer and Scanner ")
- price (NUMERIC) - Unit price
- currency (TEXT) - Currency code
- year (INTEGER) - Year of the cost data
```

**Referenced in**: `serve_supply_costs()` - calculations.py:913

**Note**: Item names appear to have trailing spaces in the original data.

---

### 5. costs_transport

Stores vehicle operating costs and fuel consumption data.

```sql
Columns:
- vehicle_model (TEXT) - Vehicle model name (e.g., "Toyota Hiace passenger van", "Corolla sedan 2014 model")
- operating_cost_per_km (NUMERIC) - Operating cost per kilometer
- consumption_litres_per_km (NUMERIC) - Fuel consumption in litres per kilometer
- currency (TEXT) - Currency code
- year (INTEGER) - Year of the cost data
```

**Referenced in**:
- `serve_vehicle_operating_cost()` - calculations.py:963
- `serve_vehicle_fuel_consumption()` - calculations.py:994

---

### 6. distance_between_regions

Stores distance metrics between regions within countries.

```sql
Columns:
- ISO3 (TEXT) - ISO3 country code
- DDist95 (NUMERIC) - Distance metric (95th percentile distance between regions in km)
- [Possibly other DDist columns...]
```

**Referenced in**: `serve_distance_between_regions()` - calculations.py:1026

**Note**: The code references `DDist95` specifically, but other distance columns may exist.

---

### 7. costs_per_diems

Stores per diem rates by country and administrative level.

```sql
Columns:
- ISO3 (TEXT) - ISO3 country code
- dsa_national (NUMERIC) - Per diem rate for national level
- dsa_upper (NUMERIC) - Per diem rate for provincial level
- dsa_lower (NUMERIC) - Per diem rate for district level
- currency (TEXT) - Currency code
- year (INTEGER) - Year of the cost data
- local_proportion (NUMERIC) - Proportion applied for local per diems (multiplier)
```

**Referenced in**: `serve_per_diem()` - calculations.py:1127

---

### 8. economic_statistics

Stores World Bank economic indicators with yearly data from 1960-2021.

```sql
Columns:
- "Country Code" (TEXT) - ISO3 country code
- "Series Name" (TEXT) - Type of economic indicator, including:
  * "PPP conversion factor, GDP (LCU per international $)"
  * "GDP deflator (base year varies by country)"
  * "GDP per capita, PPP (current international $)"
- [4 metadata columns before year data]
- "1960 [YR1960]" through "2021 [YR2021]" (NUMERIC) - Year columns containing values
```

**Referenced in**:
- `rebase_currency()` - calculations.py:1228, 1248
- `serve_gdp_per_capita()` - calculations.py:1411

**Note**: This table has a wide format with separate columns for each year from 1960 to 2021.

---

### 9. healthcare_facilities

Stores counts of different types of healthcare facilities by country.

```sql
Columns:
- ISO3 (TEXT) - ISO3 country code
- regional_hospitals (INTEGER) - Count of regional hospitals
- provincial_hospitals (INTEGER) - Count of provincial hospitals
- district_hospitals (INTEGER) - Count of district hospitals
- health_centres (INTEGER) - Count of health centres
- health_posts (INTEGER) - Count of health posts
```

**Referenced in**: `serve_healthcare_facilities()` - calculations.py:1318

**Used for**: Wall poster distribution in media campaigns (calculations.py:675-709)

---

## Data Sources

- **Original Excel File**: `5 WHO_CHOICE_Price_Database_2019_A3.xlsx`
- **Database Location**: `./data/who_choice_price_database.db`
- **Database Type**: SQLite 3

## Notes

- Currency codes appear to use ISO3 country codes (e.g., "USA" for USD)
- The `rebase_currency()` function converts "USD" to "USA" for lookups (calculations.py:1189-1193)
- Economic statistics data is limited to years 1960-2021
- Population data covers years 1950-2100
