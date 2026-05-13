"""
Upload scraped OnlineJobs.ph CSV data to a Google Sheet.

Reads the most recent scraped CSV from .tmp/ and writes it to the
sheet specified in GOOGLE_SHEETS_ID. Clears existing content first,
then writes a fresh header + all rows.

Requirements:
    pip install gspread google-auth
    Place your Service Account JSON key at: credentials.json (project root)

Usage:
    python tools/upload_to_sheets.py                          # uploads latest full scrape
    python tools/upload_to_sheets.py --csv .tmp/onlinejobs_2026-05-09_to_2026-05-13.csv
    python tools/upload_to_sheets.py --tab "May 9-13"         # write to a specific tab name
"""

import argparse
import csv
import os
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

ENV_PATH = Path(__file__).parent.parent / ".env"
CREDS_PATH = Path(__file__).parent.parent / "credentials.json"
DEFAULT_CSV = Path(__file__).parent.parent / ".tmp" / "onlinejobs_ai_automation.csv"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

load_dotenv(ENV_PATH)


def get_sheet(sheet_id: str, tab_name: str | None):
    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    if tab_name:
        try:
            worksheet = spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            print(f"  Created new tab: '{tab_name}'")
    else:
        worksheet = spreadsheet.sheet1

    return worksheet


def load_csv(csv_path: Path) -> list[list[str]]:
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Path to CSV file to upload")
    parser.add_argument("--tab", help="Sheet tab name (default: first tab)")
    args = parser.parse_args()

    sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "").strip()
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID is not set in .env")

    if not CREDS_PATH.exists():
        raise FileNotFoundError(
            f"Service account credentials not found at: {CREDS_PATH}\n"
            "See instructions in the README or ask Claude for setup steps."
        )

    csv_path = Path(args.csv) if args.csv else DEFAULT_CSV
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print(f"Loading CSV: {csv_path}")
    rows = load_csv(csv_path)
    print(f"  {len(rows) - 1} data rows + 1 header")

    print(f"Connecting to sheet: {sheet_id}")
    worksheet = get_sheet(sheet_id, args.tab)

    print(f"  Writing to tab: '{worksheet.title}'")
    worksheet.clear()
    worksheet.update(rows, value_input_option="USER_ENTERED")

    print(f"Done. {len(rows) - 1} rows written to Google Sheets.")
    print(f"  https://docs.google.com/spreadsheets/d/{sheet_id}")


if __name__ == "__main__":
    main()
