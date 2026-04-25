"""Read back current sheet state to verify setup was applied correctly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sheets_client import open_sheet

EXPECTED = {
    "Latest": 15,
    "History": 9,
    "Watchlist": 5,
}


def main() -> int:
    sh = open_sheet()
    print(f"Sheet: {sh.title}")
    print(f"Tabs found: {[ws.title for ws in sh.worksheets()]}\n")

    failures = []
    for tab, expected_cols in EXPECTED.items():
        try:
            ws = sh.worksheet(tab)
        except Exception as exc:
            failures.append(f"  [MISSING] {tab}: {exc}")
            continue
        headers = ws.row_values(1)
        status = "OK " if len(headers) == expected_cols else "BAD"
        print(f"[{status}] {tab}: {len(headers)} cols (expected {expected_cols})")
        print(f"        headers: {headers}")
        if len(headers) != expected_cols:
            failures.append(f"{tab}: got {len(headers)}, expected {expected_cols}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f)
        return 1
    print("\nAll tabs verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
