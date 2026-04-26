"""Itemku marketplace collector (Indonesian, prices in IDR).

Itemku is a Next.js app — every game category page server-side renders a
`__NEXT_DATA__` JSON blob containing products + totalItems. No private API,
no anti-bot beyond a normal User-Agent.

ITEM-FOCUSED MODE: Itemku has no uniform "item" path. Each game exposes its own
item categories under `gameInfo.item_type[]` (e.g. Blox Fruits has `fruit`,
Adopt Me has `pet`). We discover those, skip the `akun` (account) entry, and
aggregate prices across the remaining item categories. Games with no non-akun
item categories are reported as matched=False so the pipeline filters them out.

Strategy:
  1. Parse Itemku sitemap once to discover all Roblox game slugs (~87).
  2. For each Roblox game from our top list, fuzzy-match name -> Itemku slug.
  3. Fetch `/g/<slug>` to read gameInfo.item_type[] -> list of non-akun item slugs.
  4. For each item slug, fetch `/g/<slug>/<item_slug>` and combine products.
  5. Aggregate per game: avg / median price IDR, total listings, etc.

Pagination via query params doesn't work (Itemku uses XHR for page 2+).
First-page sample per category is sorted by relevance and sufficient for baseline.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

import requests

SITEMAP_INDEX = "https://www.itemku.com/sitemap.xml"
PRODUCT_LIST_PATTERN = re.compile(r"product_list[/-]")
LOC_PATTERN = re.compile(r"<loc>([^<]+)</loc>")
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
REQUEST_TIMEOUT = 25
PAGE_DELAY_S = 0.5


@dataclass
class ItemkuGameStats:
    game: str                    # canonical name (from caller)
    itemku_slug: str = ""
    item_categories: list[str] = field(default_factory=list)  # non-akun slugs aggregated
    matched: bool = False
    total_listings: int = 0      # sum of totalItems across item categories
    sample_size: int = 0         # how many products we actually loaded
    avg_price_idr: float = 0.0
    median_price_idr: float = 0.0
    min_price_idr: int = 0
    max_price_idr: int = 0
    sum_order_count: int = 0     # sum of order_count across the sample
    sample_titles: list[str] = field(default_factory=list)
    itemku_link: str = ""
    products: list[dict] = field(default_factory=list)  # raw products for per-item matcher

    def to_dict(self) -> dict:
        return {
            "game": self.game,
            "itemku_slug": self.itemku_slug,
            "item_categories": self.item_categories,
            "matched": self.matched,
            "total_listings": self.total_listings,
            "sample_size": self.sample_size,
            "avg_price_idr": round(self.avg_price_idr, 0),
            "median_price_idr": round(self.median_price_idr, 0),
            "min_price_idr": self.min_price_idr,
            "max_price_idr": self.max_price_idr,
            "sum_order_count": self.sum_order_count,
            "itemku_link": self.itemku_link,
        }


def _normalize_name(s: str) -> str:
    """Lowercase, strip emojis/brackets/punctuation, glue apostrophes, collapse spaces."""
    s = s.lower()
    s = re.sub(r"\[[^\]]*\]", "", s)         # [tags]
    s = s.replace("'", "").replace("`", "")  # sol's -> sols
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _name_variants(n: str) -> list[str]:
    """Return name + plural/singular variants for tolerant matching."""
    out = [n]
    if n.endswith("s"):
        out.append(n[:-1])
    else:
        out.append(n + "s")
    return out


def _load_overrides(path: str | Path | None = None) -> dict[str, str]:
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "data" / "itemku_overrides.json"
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return {k: v for k, v in raw.items() if not k.startswith("_")}
    except FileNotFoundError:
        return {}


def _slug_to_normalized(slug: str) -> str:
    """itemku slug -> normalized canonical name (drop 'roblox' affix)."""
    n = slug.replace("-", " ").lower()
    return re.sub(r"\broblox\b", "", n).strip()


def fetch_roblox_slugs() -> dict[str, str]:
    """Parse Itemku's sitemap; return {normalized_name: itemku_slug} for Roblox games."""
    r = requests.get(SITEMAP_INDEX, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    sub_sitemaps = [u for u in LOC_PATTERN.findall(r.text) if PRODUCT_LIST_PATTERN.search(u)]

    slugs: set[str] = set()
    for sm in sub_sitemaps:
        rr = requests.get(sm, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        if rr.status_code != 200:
            continue
        for url in LOC_PATTERN.findall(rr.text):
            if "roblox" not in url.lower():
                continue
            path = urlparse(url).path
            m = re.match(r"^/g/([^/]+)", path)
            if not m:
                continue
            slug = m.group(1)
            if slug.lower() == "roblox":
                continue
            slugs.add(slug)
        time.sleep(PAGE_DELAY_S)

    return {_slug_to_normalized(s): s for s in slugs}


def _fetch_next_data(url: str) -> dict:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    m = NEXT_DATA_PATTERN.search(r.text)
    if not m:
        raise RuntimeError(f"no __NEXT_DATA__ in {url}")
    return json.loads(m.group(1))


EXCLUDED_CATEGORY_SUBSTRINGS = ("akun", "joki", "jasa", "buddy", "boost", "coaching", "leveling")


def _list_item_categories(parent_pp: dict) -> list[str]:
    """Return tradable item slugs (drop accounts, boosting/coaching services)."""
    item_types = (parent_pp.get("gameInfo") or {}).get("item_type") or []
    out: list[str] = []
    for it in item_types:
        slug = (it.get("slug") or "").strip().lower()
        if not slug:
            continue
        if any(bad in slug for bad in EXCLUDED_CATEGORY_SUBSTRINGS):
            continue
        out.append(slug)
    return out


def fetch_game_stats(canonical_name: str, slug: str) -> ItemkuGameStats:
    """Fetch ITEM-only stats: discover non-akun categories, aggregate across them."""
    parent_url = f"https://www.itemku.com/g/{slug}"
    parent = _fetch_next_data(parent_url)
    parent_pp = parent.get("props", {}).get("pageProps", {})
    item_slugs = _list_item_categories(parent_pp)

    if not item_slugs:
        # Game exists on Itemku but only sells accounts -> not an item-tradable game here.
        return ItemkuGameStats(
            game=canonical_name,
            itemku_slug=slug,
            item_categories=[],
            matched=False,
            itemku_link=parent_url,
        )

    all_products: list[dict] = []
    total = 0
    first_item_slug = item_slugs[0]
    for it_slug in item_slugs:
        try:
            data = _fetch_next_data(f"https://www.itemku.com/g/{slug}/{it_slug}")
        except Exception:
            continue
        pp = data.get("props", {}).get("pageProps", {})
        prods = pp.get("products") or []
        all_products.extend(prods)
        total += int(pp.get("totalItems") or 0)
        time.sleep(PAGE_DELAY_S)

    prices = [int(p.get("price")) for p in all_products
              if isinstance(p.get("price"), (int, float)) and p.get("price")]
    orders = sum(int(p.get("order_count") or 0) for p in all_products)
    titles = [(p.get("name") or "")[:80] for p in all_products[:3]]

    return ItemkuGameStats(
        game=canonical_name,
        itemku_slug=slug,
        item_categories=item_slugs,
        matched=bool(all_products),
        total_listings=total,
        sample_size=len(all_products),
        avg_price_idr=(sum(prices) / len(prices)) if prices else 0.0,
        median_price_idr=float(median(prices)) if prices else 0.0,
        min_price_idr=min(prices) if prices else 0,
        max_price_idr=max(prices) if prices else 0,
        sum_order_count=orders,
        sample_titles=titles,
        itemku_link=f"https://www.itemku.com/g/{slug}/{first_item_slug}",
        products=all_products,
    )


def match_and_collect(
    canonical_names: list[str],
    slug_directory: dict[str, str] | None = None,
) -> dict[str, ItemkuGameStats]:
    """For each name, find best slug match and collect stats."""
    if slug_directory is None:
        slug_directory = fetch_roblox_slugs()
    overrides = _load_overrides()

    out: dict[str, ItemkuGameStats] = {}
    for name in canonical_names:
        slug = overrides.get(name)
        if not slug:
            n = _normalize_name(name)
            for variant in _name_variants(n):
                if variant in slug_directory:
                    slug = slug_directory[variant]
                    break
        if not slug:
            # fuzzy: token-set subset (handles re-orderings and trailing-s mismatches via variants)
            tokens = set(_normalize_name(name).split())
            best, best_score = None, 0
            for nn, s in slug_directory.items():
                ttokens = set(nn.split())
                if not tokens.issubset(ttokens) and not ttokens.issubset(tokens):
                    continue
                score = len(tokens & ttokens)
                if score > best_score:
                    best, best_score = s, score
            slug = best

        if not slug:
            out[name] = ItemkuGameStats(game=name, matched=False)
            continue
        try:
            out[name] = fetch_game_stats(name, slug)
        except Exception as exc:
            out[name] = ItemkuGameStats(game=name, itemku_slug=slug, matched=False, sample_titles=[f"ERROR: {exc}"])
        time.sleep(PAGE_DELAY_S)
    return out
