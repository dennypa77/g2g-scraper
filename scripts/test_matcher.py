"""Smoke test for the per-item matcher.

Runs the same fetch the full pipeline does — but only for ONE game — and prints
the cross-matched rows so you can eyeball the pairings (Itemku item <-> G2G
offer) without writing to Sheets. Useful for tuning thresholds.

Usage:
    python scripts/test_matcher.py                # default: Bee Swarm Simulator
    python scripts/test_matcher.py "Blox Fruits"  # any canonical name from data/game_aliases.json
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.g2g import collect as g2g_collect, load_aliases
from src.collectors.itemku import match_and_collect as itemku_collect
from src.exchange import fetch_usd_to_idr
from src.matcher import match_per_game


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "Bee Swarm Simulator"

    aliases = load_aliases()
    if target not in aliases:
        print(f"  ERROR: '{target}' not in data/game_aliases.json")
        print(f"  Available: {', '.join(aliases)}")
        return 1

    print(f"Target game: {target}\n")

    print("[1/3] Fetching G2G Roblox marketplace...")
    g2g_offers, g2g_stats = g2g_collect()
    gs = g2g_stats.get(target)
    if not gs or not gs.offers:
        print(f"  No G2G offers matched '{target}'. Aborting.")
        return 2
    print(f"      {len(gs.offers)} G2G offers in '{target}' bucket")

    print("[2/3] Fetching Itemku products for this game...")
    itemku_stats = itemku_collect([target])
    ik = itemku_stats.get(target)
    if not ik or not ik.matched or not ik.products:
        print(f"  No Itemku products matched '{target}'. Aborting.")
        return 3
    print(f"      {len(ik.products)} Itemku products (slug={ik.itemku_slug})")

    rate = fetch_usd_to_idr()
    print(f"      USD->IDR rate: {rate:,.2f}\n")

    print("[3/3] Cross-matching items...")
    matches = match_per_game(target, ik.products, gs.offers)
    matches.sort(key=lambda m: m.g2g_median_usd * rate - m.itemku_price_idr, reverse=True)

    if not matches:
        print("  (no matches above threshold)")
        return 0

    print(f"\n{'Item (Itemku)':50s} {'IDR Buy':>10} {'G2G$Med':>9} "
          f"{'Sell IDR':>11} {'Margin%':>9} {'Profit':>10} {'Conf':>5} {'#G2G':>5}")
    print("-" * 120)
    for m in matches[:50]:
        sell_idr = m.g2g_median_usd * rate
        margin = ((sell_idr - m.itemku_price_idr) / m.itemku_price_idr * 100) if m.itemku_price_idr else 0
        profit = int(round(sell_idr - m.itemku_price_idr))
        print(
            f"{m.itemku_name[:48]:50s} "
            f"{m.itemku_price_idr:>10,} "
            f"{m.g2g_median_usd:>9.2f} "
            f"{int(round(sell_idr)):>11,} "
            f"{margin:>8.1f}% "
            f"{profit:>10,} "
            f"{m.match_confidence:>5.2f} "
            f"{m.g2g_match_count:>5}"
        )

    print(f"\nTotal matches: {len(matches)} (showing top 50 by absolute profit)")
    print("Sample G2G title for top row:")
    if matches:
        print(f"  {matches[0].g2g_best_title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
