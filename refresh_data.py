"""
Refresh events_data.json from Google Sheets.

Requirements:
    pip3 install gspread

First run: opens your browser for Google authorization.
Credentials are cached in ~/.config/gspread/ for future runs.

Usage:
    python3 refresh_data.py
"""

import json
import os
from datetime import datetime

try:
    import gspread
except ImportError:
    print("gspread not installed. Run: pip3 install gspread")
    raise

SPREADSHEET_ID = "1r1B4Mg4uf3WyGN4zXClzCXrgklVTzPyxQlGcoUToNVI"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "events_data.json")

COLUMNS = [
    "Timeline", "Chapter Name", "Chapter Leader", "Snowflake SE PoC",
    "Marketo Email Blast - 1", "Marketo Email Blast - 2", "Bevy Email Blast",
    "Date of Event", "Venue", "Reg link", "Registrations", "Attendance", "Feedback",
]


def to_value(v: str):
    if v == "" or v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        pass
    return v


def main():
    print("Connecting to Google Sheets...")
    gc = gspread.oauth()
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.sheet1

    records = ws.get_all_records(expected_headers=COLUMNS)

    events = []
    for r in records:
        events.append({col: to_value(r.get(col, "")) for col in COLUMNS})

    payload = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "events": events,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved {len(events)} events to {OUTPUT_FILE}")
    print(f"Last updated: {payload['last_updated']}")


if __name__ == "__main__":
    main()
