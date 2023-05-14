import json
import sqlite3
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()

origins = [
    "https://pc.forecasthealth.org",
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

@app.post("/process")
async def process(item: Item):
    data = {**DEFAULTS, **item.dict()}
    conn = load_database()
    logs, table = runtime.run(data, conn)
    table_filename = "output.csv"
    table.to_csv(table_filename, index=False, encoding='utf-8')
    logs_filename = "output_logs.txt"
    with open(logs_filename, "w") as f:
        for s in logs:
            f.write(s + "\n")
    with open(table_filename, "r") as f:  
        csv_content = f.read()
    return PlainTextResponse(csv_content)

