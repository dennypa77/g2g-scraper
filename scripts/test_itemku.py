"""Smoke test for Itemku collector — match top games & print IDR stats."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.itemku import fetch_roblox_slugs, match_and_collect


GAMES = [
    "Blox Fruits", "Adopt Me!", "Brookhaven RP", "Pet Simulator 99",
    "Pet Simulator X", "Grow a Garden", "Steal a Brainrot", "Murder Mystery 2",
    "Jujutsu Shenanigans", "Sol's RNG", "RIVALS", "99 Nights in the Forest",
    "Dress to Impress", "Forsaken", "Fish It!", "The Strongest Battlegrounds",
    "Anime Defenders", "Anime Vanguards", "Blade Ball", "Doors",
    "Combat Warriors", "Royale High", "Tower of Hell", "Bee Swarm Simulator",
    "King Legacy", "Jailbreak",
]


def main() -> int:
    print("Step 1/2: discovering Itemku Roblox slug directory from sitemap...")
    slugs = fetch_roblox_slugs()
    print(f"  -> {len(slugs)} Roblox games on Itemku\n")

    print("Step 2/2: matching + fetching stats per game...")
    stats = match_and_collect(GAMES, slug_directory=slugs)

    matched = [s for s in stats.values() if s.matched]
    unmatched = [s for s in stats.values() if not s.matched]
    print(f"\nMatched {len(matched)}/{len(GAMES)} games.")

    rows = sorted(matched, key=lambda s: s.total_listings, reverse=True)
    print(f"\n{'Game':30s} {'Slug':35s} {'Total':>7} {'Avg IDR':>13} {'Median':>13} {'Orders(sample)':>15}")
    print("-" * 120)
    for s in rows:
        print(
            f"{s.game[:28]:30s} {s.itemku_slug[:33]:35s} {s.total_listings:>7} "
            f"{s.avg_price_idr:>13,.0f} {s.median_price_idr:>13,.0f} {s.sum_order_count:>15,}"
        )

    if unmatched:
        print(f"\nUnmatched ({len(unmatched)}):")
        for s in unmatched:
            print(f"  - {s.game}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
