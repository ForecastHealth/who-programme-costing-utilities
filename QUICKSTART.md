# Quick Start - Database Recreation

## To recreate the database from scratch:

### Prerequisites
- `CountryData.db` in the root directory
- `data/raw.xlsx` (the WHO CHOICE Price Database Excel file)

### Steps

```bash
# 1. Populate database from Excel file
python3 scripts/populate_database.py

# 2. Migrate data from CountryData.db
python3 scripts/migrate_country_data.py
```

### Result
- Database created at: `./data/who_choice_price_database.db`
- All 9 tables populated with 32,532 total rows

### File Structure
```
who-programme-costing-utilities/
├── CountryData.db                      # Source for economic & population data
├── data/
│   ├── raw.xlsx                        # WHO CHOICE Excel workbook
│   ├── who_choice_price_database.db    # Generated database
│   └── personnel_cadre.json            # Personnel role to cadre mapping
├── scripts/
│   ├── populate_database.py            # Extract from Excel
│   └── migrate_country_data.py         # Migrate from CountryData.db
├── docs/
│   ├── database_schemas.md             # Table schema documentation
│   ├── DATABASE_RECOVERY.md            # Detailed recovery guide
│   └── MIGRATION_SUMMARY.md            # Migration summary
└── programme_costing_utilities/        # Application code
```

### Verification

```bash
# Check all tables are populated
python3 -c "
import sqlite3
conn = sqlite3.connect('./data/who_choice_price_database.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
for table in cursor.fetchall():
    cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
    print(f'{table[0]}: {cursor.fetchone()[0]} rows')
conn.close()
"
```

### Documentation
- **Schemas**: See `docs/database_schemas.md`
- **Recovery Guide**: See `docs/DATABASE_RECOVERY.md`
- **Migration Summary**: See `docs/MIGRATION_SUMMARY.md`

### Usage

```bash
# Run the cost calculator
python3 main.py -i your_input.json -o output

# Or start the API server
python3 api.py
```
