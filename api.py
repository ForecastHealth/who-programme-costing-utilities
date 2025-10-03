import json
import sqlite3
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
    "end_year": 2100,
    "discount_rate": 1.03,
    "desired_currency": "USD",
    "desired_year": 2018,
    "components": {
        "personnel": default_personnel,
        "meetings": default_meetings,
        "media": default_media
    }
}

def load_database():
    conn = sqlite3.connect('./data/who_choice_price_database.db')
    return conn

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

origins = [
    "https://pc.forecasthealth.org",
    "https://pcapi.forecasthealth.org",
    "http://localhost",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    country: str
    start_year: int
    end_year: int
    discount_rate: float
    desired_currency: str
    desired_year: int

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def fetch_single_column(query: str, conn: sqlite3.Connection) -> List[str]:
    cursor = conn.cursor()
    cursor.execute(query)
    return sorted(set(row[0] for row in cursor.fetchall() if row and row[0]))


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = BASE_DIR / "static" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Client not bundled")
    return index_path.read_text(encoding="utf-8")


@app.get("/meta/options", response_class=JSONResponse)
async def get_options():
    conn = load_database()
    try:
        countries = fetch_single_column(
            "SELECT ISO3 FROM administrative_divisions ORDER BY ISO3", conn
        )

        currencies = fetch_single_column(
            'SELECT DISTINCT "Country Code" FROM "economic_statistics"', conn
        )
        currencies.extend(["USD", "I$"])
        currencies = sorted(set(currencies))

        cursor = conn.cursor()
        cursor.execute("SELECT MIN(Time), MAX(Time) FROM population")
        min_year, max_year = cursor.fetchone()

        response = {
            "defaults": DEFAULTS,
            "countries": countries,
            "currencies": currencies,
            "year_range": {
                "min": int(min_year) if min_year is not None else 1950,
                "max": int(max_year) if max_year is not None else 2100
            }
        }
    finally:
        conn.close()

    return response


@app.post("/process")
async def process(item: Item):
    data = {**DEFAULTS, **item.dict()}
    conn = load_database()
    try:
        logs, table = runtime.run(data, conn)
    finally:
        conn.close()

    table_filename = "output.csv"
    table.to_csv(table_filename, index=False, encoding='utf-8')
    logs_filename = "output_logs.txt"
    with open(logs_filename, "w", encoding="utf-8") as f:
        for s in logs:
            f.write(s + "\n")
    with open(table_filename, "r", encoding="utf-8") as f:
        csv_content = f.read()
    return PlainTextResponse(csv_content)
