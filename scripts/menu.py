"""Interactive menu for running G2G-bot tools locally.

Usage:
    python scripts/menu.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

MENU = [
    ("1", "Full scan (Roblox + G2G + Itemku -> Sheets)", "run_scan.py"),
    ("2", "Test Google Sheets connection",                "test_connection.py"),
    ("3", "Setup / verify Sheet tabs (Latest, History, Watchlist)", "setup_tabs.py"),
    ("4", "Verify current Sheet state",                   "verify_state.py"),
    ("5", "Test Roblox collector (popular games + CCU)",  "test_roblox.py"),
    ("6", "Test G2G collector (item offers)",             "test_g2g.py"),
    ("7", "Test Itemku collector (per-game items)",       "test_itemku.py"),
    ("8", "Show live USD/IDR exchange rate",              None),
    ("0", "Exit",                                          None),
]


def show_exchange_rate() -> None:
    sys.path.insert(0, str(ROOT))
    from src.exchange import fetch_usd_to_idr
    rate = fetch_usd_to_idr()
    print(f"\n  USD -> IDR: Rp {rate:,.2f}")
    print(f"  $10 ~= Rp {rate*10:,.0f}")
    print(f"  $50 ~= Rp {rate*50:,.0f}")


def run_script(name: str) -> int:
    path = SCRIPTS / name
    if not path.exists():
        print(f"  ERROR: {path} not found")
        return 1
    return subprocess.call([sys.executable, str(path)], cwd=ROOT)


def main() -> int:
    while True:
        print("\n" + "=" * 60)
        print("  G2G-BOT  -  Interactive Menu")
        print("=" * 60)
        for key, label, _ in MENU:
            print(f"  [{key}] {label}")
        print()
        choice = input("  Choose (0-8): ").strip()

        match = next((m for m in MENU if m[0] == choice), None)
        if not match:
            print("  Invalid choice.")
            continue

        key, label, script = match
        if key == "0":
            print("  Bye.")
            return 0
        if key == "8":
            show_exchange_rate()
            continue

        print(f"\n>>> Running: {label}\n")
        rc = run_script(script)
        print(f"\n<<< Done (exit {rc})")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        raise SystemExit(130)
