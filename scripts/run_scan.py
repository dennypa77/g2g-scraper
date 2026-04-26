"""Pipeline runner — chain all collectors and update Sheets Latest + History.

Steps:
  1. Roblox: fetch popular games + CCU
  2. G2G:    fetch all rbl-item offers, aggregate per canonical game (via aliases)
  3. Itemku: per canonical game, fetch IDR price stats + raw products
  4. Combine + compute Margin% and Score (per-game)
  5. Cross-match individual items (Itemku product <-> G2G offer) for arbitrage
  6. Write to `Latest` (clear+rewrite), `History` (append), and `Items` (clear+rewrite)
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from math import log
from pathlib import Path

WIB = timezone(timedelta(hours=7), name="WIB")  # Asia/Jakarta, no DST

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.g2g import collect as g2g_collect, load_aliases
from src.collectors.itemku import match_and_collect as itemku_collect
from src.collectors.roblox import collect_popular_games, enrich_with_details
from src.exchange import fetch_usd_to_idr
from src.matcher import match_per_game
from src.sheets_client import get_or_create_tab, open_sheet

LATEST_TAB = "Latest"
HISTORY_TAB = "History"
ITEMS_TAB = "Items"
LATEST_COL_RANGE = "O"           # 15 columns A..O
HISTORY_COL_RANGE = "I"          # 9 columns A..I
ITEMS_COL_RANGE = "P"            # 16 columns A..P
ITEMS_MAX_ROWS = 1000            # cap to keep the sheet snappy
TOP_ROBLOX_LIMIT = 100           # how many Roblox games to enrich with details

ITEMS_HEADERS = [
    "Game Name", "Item Name (Itemku)", "Itemku Price (IDR)",
    "G2G Min (USD)", "G2G Min (IDR equiv)",
    "G2G Median (USD)", "G2G Median (IDR equiv)",
    "Margin %", "Profit per Unit (IDR)", "Itemku Order Count",
    "G2G Match Count", "Match Confidence", "G2G Sample Title",
    "Itemku Link", "G2G Link", "Last Updated WIB",
]


def _find_roblox_match(canonical: str, aliases: list[str], roblox_games: list) -> object | None:
    """Return the Roblox game with the highest CCU whose name matches any alias."""
    keywords = [canonical.lower()] + [a.lower() for a in aliases]
    matched = [g for g in roblox_games if any(kw in g.name.lower() for kw in keywords)]
    return max(matched, key=lambda g: g.ccu) if matched else None


def _score(margin_pct: float, lifetime_orders: int, ccu: int) -> float:
    """Composite: positive margin x sales velocity x demand signal."""
    if margin_pct <= 0:
        return 0.0
    return round(margin_pct * log(1 + lifetime_orders) * log(1 + ccu) / 100.0, 2)


def main() -> int:
    print("[1/6] Fetching Roblox popular games...")
    roblox = collect_popular_games(min_ccu=500)
    print(f"      {len(roblox)} games (CCU >= 500)")
    enrich_with_details(roblox[:TOP_ROBLOX_LIMIT])

    print("[2/6] Fetching G2G Roblox marketplace...")
    g2g_offers, g2g_stats = g2g_collect()
    print(f"      {len(g2g_offers)} offers; aggregated into {len(g2g_stats)} game buckets")

    print("[3/6] Fetching Itemku per-game stats...")
    aliases = load_aliases()
    canonical_names = list(aliases.keys())
    itemku_stats = itemku_collect(canonical_names)
    matched_ik = sum(1 for s in itemku_stats.values() if s.matched)
    print(f"      {matched_ik}/{len(canonical_names)} matched on Itemku")

    rate = fetch_usd_to_idr()
    print(f"      USD->IDR exchange rate: {rate:,.2f}")

    print("[4/6] Combining + computing per-game margin/score...")
    now_wib = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
    rows: list[list] = []

    for canonical, alias_kws in aliases.items():
        rb = _find_roblox_match(canonical, alias_kws, roblox)
        gs = g2g_stats.get(canonical)
        ik = itemku_stats.get(canonical)

        ccu = rb.ccu if rb else 0
        place_id = rb.place_id if rb else 0
        roblox_link = f"https://www.roblox.com/games/{place_id}/" if place_id else ""

        g2g_avg_usd = gs.avg_price_usd if gs else 0.0
        g2g_med_usd = gs.median_price_usd if gs else 0.0
        g2g_sellers = gs.unique_sellers if gs else 0
        g2g_lifetime = gs.sum_lifetime_orders if gs else 0
        tradable = bool(gs and gs.matched_offer_count > 0)
        g2g_link = (gs.g2g_link if gs else "https://www.g2g.com/categories/rbl-account")

        itemku_avg_idr = int(ik.avg_price_idr) if ik and ik.matched else 0
        itemku_med_idr = int(ik.median_price_idr) if ik and ik.matched else 0
        itemku_link = ik.itemku_link if ik and ik.matched else ""

        # Use medians (robust to whale outliers) for the margin calculation
        if g2g_med_usd > 0 and itemku_med_idr > 0:
            cost_usd = itemku_med_idr / rate
            margin_pct = (g2g_med_usd - cost_usd) / cost_usd * 100
        else:
            margin_pct = 0.0

        score = _score(margin_pct, g2g_lifetime, ccu)

        # Item-focused filter: require G2G item presence (the bot's primary
        # arbitrage signal). Games without G2G item offers are skipped even if
        # they have Roblox CCU or Itemku listings.
        if not (gs and gs.matched_offer_count > 0):
            continue

        rows.append([
            canonical,                     # Game Name
            ccu,                           # CCU
            "Yes" if tradable else "No",   # Tradable
            g2g_lifetime,                  # G2G Sold Count 30d (lifetime placeholder until History delta works)
            "",                            # Icon
            round(g2g_avg_usd, 2),         # G2G Avg Price (USD)
            itemku_avg_idr,                # Itemku Avg Price (IDR)
            round(margin_pct, 1),          # Margin %
            g2g_sellers,                   # G2G Sellers
            score,                         # Score
            "",                            # Trend 7d
            roblox_link,                   # Roblox Link
            g2g_link,                      # G2G Link
            itemku_link,                   # Itemku Link
            now_wib,                       # Last Updated WIB
        ])

    rows.sort(key=lambda r: (r[9], r[1]), reverse=True)  # by Score desc, then CCU desc
    print(f"      {len(rows)} rows ready")

    print("[5/6] Computing per-item arbitrage opportunities...")
    item_rows: list[list] = []
    for canonical in aliases:
        gs = g2g_stats.get(canonical)
        ik = itemku_stats.get(canonical)
        if not (gs and gs.offers):
            continue
        if not (ik and ik.matched and ik.products):
            continue

        matches = match_per_game(canonical, ik.products, gs.offers)
        for m in matches:
            cost_idr = m.itemku_price_idr
            sell_idr_min = m.g2g_min_usd * rate
            sell_idr_med = m.g2g_median_usd * rate
            margin_pct = ((sell_idr_med - cost_idr) / cost_idr * 100) if cost_idr > 0 else 0.0
            profit_idr = int(round(sell_idr_med - cost_idr))

            item_rows.append([
                canonical,                              # Game Name
                m.itemku_name[:120],                    # Item Name
                cost_idr,                               # Itemku Price (IDR)
                round(m.g2g_min_usd, 2),                # G2G Min (USD)
                int(round(sell_idr_min)),               # G2G Min (IDR equiv)
                round(m.g2g_median_usd, 2),             # G2G Median (USD)
                int(round(sell_idr_med)),               # G2G Median (IDR equiv)
                round(margin_pct, 1),                   # Margin %
                profit_idr,                             # Profit per Unit (IDR)
                m.itemku_order_count,                   # Itemku Order Count
                m.g2g_match_count,                      # G2G Match Count
                m.match_confidence,                     # Match Confidence
                m.g2g_best_title,                       # G2G Sample Title
                ik.itemku_link,                         # Itemku Link
                gs.g2g_link,                            # G2G Link
                now_wib,                                # Last Updated WIB
            ])

    # Sort: highest margin first, ties broken by match confidence then profit
    item_rows.sort(key=lambda r: (r[7], r[11], r[8]), reverse=True)
    if len(item_rows) > ITEMS_MAX_ROWS:
        item_rows = item_rows[:ITEMS_MAX_ROWS]
    print(f"      {len(item_rows)} item-level arbitrage rows (median G2G vs Itemku)")

    print("[6/6] Writing to Sheets...")
    sh = open_sheet()

    latest = sh.worksheet(LATEST_TAB)
    latest.batch_clear([f"A2:{LATEST_COL_RANGE}1000"])
    if rows:
        latest.update(values=rows, range_name=f"A2:{LATEST_COL_RANGE}{1 + len(rows)}",
                      value_input_option="USER_ENTERED")

    history = sh.worksheet(HISTORY_TAB)
    history_rows = [[
        now_wib,    # Snapshot WIB
        r[0],       # Game Name
        r[1],       # CCU
        r[2],       # Tradable
        r[3],       # Sold (lifetime placeholder)
        r[5],       # G2G Avg USD
        r[6],       # Itemku Avg IDR
        r[7],       # Margin %
        r[9],       # Score
    ] for r in rows]
    if history_rows:
        history.append_rows(history_rows, value_input_option="USER_ENTERED")

    items = get_or_create_tab(sh, ITEMS_TAB, ITEMS_HEADERS)
    items.batch_clear([f"A2:{ITEMS_COL_RANGE}{ITEMS_MAX_ROWS + 1}"])
    if item_rows:
        items.update(values=item_rows,
                     range_name=f"A2:{ITEMS_COL_RANGE}{1 + len(item_rows)}",
                     value_input_option="USER_ENTERED")

    print(
        f"\nDONE. Wrote {len(rows)} to {LATEST_TAB}, "
        f"appended {len(history_rows)} to {HISTORY_TAB}, "
        f"wrote {len(item_rows)} to {ITEMS_TAB}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
