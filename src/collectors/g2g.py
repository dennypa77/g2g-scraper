"""G2G Roblox marketplace collector.

G2G's Roblox item category (`rbl-item`) is one umbrella — there is NO per-game
sub-category. We fetch all offers and classify them by matching keyword
aliases in the offer title (titles are formatted "Game Name > Item > Tier").

This collector targets ITEMS, not accounts. To switch back to account scraping,
change ROBLOX_SEO_TERM to "rbl-account".

Aggregate per matched game:
  - matched_offer_count    (how many live offers reference this game)
  - unique_sellers         (distinct seller_id among matched offers)
  - avg_price_usd          (mean unit_price_in_usd across matched offers)
  - median_price_usd
  - min_price_usd / max_price_usd
  - sum_lifetime_orders    (sum of total_success_order — lifetime, not 30d)

For 30d sold count, take daily snapshots and derive deltas from the History tab.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Iterable

import requests

SEARCH_URL = "https://sls.g2g.com/offer/search"
ROBLOX_SEO_TERM = "rbl-item"
DEFAULT_HEADERS = {
    "User-Agent": "g2g-roblox-bot/0.1",
    "Accept": "application/json",
}
PAGE_SIZE = 100  # API max
REQUEST_TIMEOUT = 25
PAGE_DELAY_S = 0.4


@dataclass
class G2GGameStats:
    game: str
    matched_offer_count: int = 0
    unique_sellers: int = 0
    avg_price_usd: float = 0.0
    median_price_usd: float = 0.0
    min_price_usd: float = 0.0
    max_price_usd: float = 0.0
    sum_lifetime_orders: int = 0
    sample_titles: list[str] = field(default_factory=list)
    g2g_link: str = f"https://www.g2g.com/categories/{ROBLOX_SEO_TERM}"

    @property
    def is_tradable_on_g2g(self) -> bool:
        return self.matched_offer_count > 0

    def to_dict(self) -> dict:
        return {
            "game": self.game,
            "matched_offer_count": self.matched_offer_count,
            "unique_sellers": self.unique_sellers,
            "avg_price_usd": round(self.avg_price_usd, 2),
            "median_price_usd": round(self.median_price_usd, 2),
            "min_price_usd": round(self.min_price_usd, 2),
            "max_price_usd": round(self.max_price_usd, 2),
            "sum_lifetime_orders": self.sum_lifetime_orders,
            "is_tradable_on_g2g": self.is_tradable_on_g2g,
            "g2g_link": self.g2g_link,
        }


def fetch_all_roblox_offers(
    max_pages: int = 50,
    country: str = "US",
    currency: str = "USD",
) -> list[dict]:
    """Paginate through every live Roblox offer on G2G."""
    all_offers: list[dict] = []
    for page in range(1, max_pages + 1):
        r = requests.get(
            SEARCH_URL,
            params={
                "seo_term": ROBLOX_SEO_TERM,
                "page": page,
                "page_size": PAGE_SIZE,
                "country": country,
                "currency": currency,
            },
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 400:
            # G2G returns 400 once you page past the last result
            break
        if r.status_code >= 500:
            r.raise_for_status()
        results = (r.json().get("payload") or {}).get("results") or []
        if not results:
            break
        all_offers.extend(results)
        if len(results) < PAGE_SIZE:
            break
        time.sleep(PAGE_DELAY_S)
    return all_offers


def load_aliases(path: str | Path | None = None) -> dict[str, list[str]]:
    """Load game→aliases map from data/game_aliases.json (skip _README key)."""
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "data" / "game_aliases.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: [a.lower() for a in v] for k, v in raw.items() if not k.startswith("_")}


def classify_offer(offer: dict, aliases: dict[str, list[str]]) -> str | None:
    """Return canonical game name if title matches any alias, else None."""
    title = (offer.get("title") or "").lower()
    if not title:
        return None
    for game, kws in aliases.items():
        if any(kw in title for kw in kws):
            return game
    return None


def aggregate_by_game(
    offers: Iterable[dict],
    aliases: dict[str, list[str]] | None = None,
) -> dict[str, G2GGameStats]:
    """Bucket offers per game and compute aggregate stats."""
    if aliases is None:
        aliases = load_aliases()
    buckets: dict[str, list[dict]] = {g: [] for g in aliases}
    for off in offers:
        g = classify_offer(off, aliases)
        if g:
            buckets[g].append(off)

    out: dict[str, G2GGameStats] = {}
    for game, lst in buckets.items():
        if not lst:
            out[game] = G2GGameStats(game=game)
            continue
        prices = [o.get("unit_price_in_usd") for o in lst if isinstance(o.get("unit_price_in_usd"), (int, float))]
        sellers = {o.get("seller_id") for o in lst if o.get("seller_id")}
        orders = sum(int(o.get("total_success_order") or 0) for o in lst)
        sample = [o.get("title", "")[:80] for o in lst[:3]]
        out[game] = G2GGameStats(
            game=game,
            matched_offer_count=len(lst),
            unique_sellers=len(sellers),
            avg_price_usd=(sum(prices) / len(prices)) if prices else 0.0,
            median_price_usd=median(prices) if prices else 0.0,
            min_price_usd=min(prices) if prices else 0.0,
            max_price_usd=max(prices) if prices else 0.0,
            sum_lifetime_orders=orders,
            sample_titles=sample,
        )
    return out


def collect(country: str = "US", currency: str = "USD") -> tuple[list[dict], dict[str, G2GGameStats]]:
    """One-call entry: fetch + aggregate. Returns (raw_offers, per_game_stats)."""
    offers = fetch_all_roblox_offers(country=country, currency=currency)
    stats = aggregate_by_game(offers)
    return offers, stats
