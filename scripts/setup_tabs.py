"""Idempotent: ensures Latest, History, Watchlist tabs exist with the agreed headers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sheets_client import get_or_create_tab, open_sheet

LATEST_HEADERS = [
    "Game Name",
    "CCU",
    "Tradable",
    "G2G Sold Count 30d",
    "Icon",
    "G2G Avg Price (USD)",
    "Itemku Avg Price (IDR)",
    "Margin %",
    "G2G Sellers",
    "Score",
    "Trend 7d",
    "Roblox Link",
    "G2G Link",
    "Itemku Link",
    "Last Updated WIB",
]

HISTORY_HEADERS = [
    "Snapshot WIB",
    "Game Name",
    "CCU",
    "Tradable",
    "G2G Sold Count 30d",
    "G2G Avg Price (USD)",
    "Itemku Avg Price (IDR)",
    "Margin %",
    "Score",
]

WATCHLIST_HEADERS = [
    "Game Name",
    "Notes",
    "Target Buy Price (IDR)",
    "Target Sell Price (USD)",
    "Active",
]

ITEMS_HEADERS = [
    "Game Name",
    "Item Name (Itemku)",
    "Itemku Price (IDR)",
    "G2G Min (USD)",
    "G2G Min (IDR equiv)",
    "G2G Median (USD)",
    "G2G Median (IDR equiv)",
    "Margin %",
    "Profit per Unit (IDR)",
    "Itemku Order Count",
    "G2G Match Count",
    "Match Confidence",
    "G2G Sample Title",
    "Itemku Link",
    "G2G Link",
    "Last Updated WIB",
]


def main() -> int:
    print("Opening spreadsheet...")
    sh = open_sheet()
    print(f"  -> {sh.title}")

    for title, headers in [
        ("Latest", LATEST_HEADERS),
        ("History", HISTORY_HEADERS),
        ("Watchlist", WATCHLIST_HEADERS),
        ("Items", ITEMS_HEADERS),
    ]:
        print(f"Ensuring tab '{title}' ({len(headers)} columns)...")
        get_or_create_tab(sh, title, headers)

    print("\nSUKSES. 4 tab utama siap dipakai.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
