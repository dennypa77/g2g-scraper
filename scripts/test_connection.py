"""Quick smoke test: connect to the configured Sheet and write one dummy row."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sheets_client import open_sheet


def main() -> int:
    print("[1/3] Opening spreadsheet...")
    sh = open_sheet()
    print(f"      Title: {sh.title}")
    print(f"      URL  : {sh.url}")

    print("[2/3] Selecting/creating tab '_connection_test'...")
    try:
        ws = sh.worksheet("_connection_test")
    except Exception:
        ws = sh.add_worksheet(title="_connection_test", rows=10, cols=3)
        ws.update(values=[["timestamp_utc", "source", "message"]], range_name="A1")

    print("[3/3] Appending dummy row...")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ws.append_row([now, "test_connection.py", "OK — service account dapat menulis"])

    print("\nSUKSES. Cek tab '_connection_test' di sheet Anda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
