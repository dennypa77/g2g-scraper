import os
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client() -> gspread.Client:
    sa_path = Path(os.environ["SERVICE_ACCOUNT_PATH"])
    if not sa_path.is_absolute():
        sa_path = Path(__file__).resolve().parent.parent / sa_path
    creds = Credentials.from_service_account_file(str(sa_path), scopes=SCOPES)
    return gspread.authorize(creds)


def open_sheet() -> gspread.Spreadsheet:
    client = get_client()
    return client.open_by_key(os.environ["SPREADSHEET_ID"])


def get_or_create_tab(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    headers: list[str],
) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(len(headers), 10))
        ws.update(values=[headers], range_name="A1")
        return ws
    existing = ws.row_values(1)
    if existing != headers:
        ws.update(values=[headers], range_name="A1")
    return ws
