"""Smoke test for G2G collector — fetch all Roblox offers, aggregate, print."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.g2g import collect


def main() -> int:
    print("Fetching all Roblox offers from G2G...")
    offers, stats = collect()
    print(f"  -> {len(offers)} total live offers\n")

    matched = sum(s.matched_offer_count for s in stats.values())
    print(f"Matched to a game: {matched} / {len(offers)} ({matched/max(len(offers),1):.1%})")
    print(f"Aliases configured for {len(stats)} games\n")

    rows = sorted(stats.values(), key=lambda s: s.matched_offer_count, reverse=True)
    print(f"{'Game':30s} {'#Offers':>8} {'Sellers':>8} {'Avg$':>8} {'Med$':>8} {'Min$':>7} {'Max$':>9} {'LifetimeOrders':>15}")
    print("-" * 105)
    for s in rows:
        marker = " " if s.matched_offer_count else "·"
        print(
            f"{marker} {s.game[:28]:28s} {s.matched_offer_count:>8} {s.unique_sellers:>8} "
            f"{s.avg_price_usd:>8.2f} {s.median_price_usd:>8.2f} {s.min_price_usd:>7.2f} "
            f"{s.max_price_usd:>9.2f} {s.sum_lifetime_orders:>15,}"
        )

    print("\nSample matched titles for top 3 games:")
    for s in rows[:3]:
        if s.sample_titles:
            print(f"  [{s.game}]")
            for t in s.sample_titles:
                print(f"    - {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
