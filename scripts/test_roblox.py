"""Standalone smoke test for the Roblox collector. Prints top 20 by CCU."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.roblox import collect_popular_games, enrich_with_details


def main() -> int:
    print("Fetching popular games from Roblox Explore API...")
    games = collect_popular_games(min_ccu=100)
    print(f"  -> {len(games)} unique games (CCU >= 100)\n")

    if not games:
        print("FAIL: no games returned. API may have changed.")
        return 1

    print("Enriching top 20 with details (visits, creator)...")
    top20 = games[:20]
    enrich_with_details(top20)

    print(f"\n{'CCU':>8}  {'Visits':>13}  {'Rating':>6}  Name (creator)")
    print("-" * 100)
    for g in top20:
        print(
            f"{g.ccu:>8,}  {g.visits:>13,}  {g.rating:>6.1%}  "
            f"{g.name[:55]}  ({g.creator_name})"
        )

    print(f"\nTotal universe in pool: {len(games)}")
    print(f"CCU range: {games[-1].ccu:,} .. {games[0].ccu:,}")
    print("Sort buckets seen:", sorted({s for g in games for s in g.sort_sources}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
