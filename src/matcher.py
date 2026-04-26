"""Per-item cross-platform matcher: pair an Itemku product to G2G offers of the
same item identity, within a single canonical game's bucket.

Why matching is needed: the per-game stats hide *which* items have margin —
a game's median can be flat while a specific item has 200% upside. To surface
those, we cross-match individual listings.

Algorithm: token-set Jaccard similarity after normalisation.
  1. Lowercase, strip [tags]/(parens), drop punctuation.
  2. Drop universal marketplace fluff (buy, sell, fast, roblox, ...).
  3. Drop the canonical game-name tokens + their singular/plural twins
     (so "Bee Swarm Simulator" tokens don't drown out "disco" vs "tadpole").
  4. Jaccard on the surviving sets; require at least 1 shared distinguishing
     token AND jaccard >= MIN_JACCARD.

We deliberately do NOT strip the alias list — aliases like "huge cat" or
"dragon fruit" are item-level signals, not game-level. Stripping them would
erase the very tokens we match on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median
from typing import Iterable

# Marketplace/service fluff that never identifies an item
STOPWORDS = frozenset({
    "roblox", "rblx", "rbx",
    "buy", "sell", "selling", "stock", "order", "ready", "delivery",
    "fast", "instant", "cheap", "trusted", "safe", "secure", "promo",
    "auto", "manual", "guarantee", "guaranteed", "live",
    "murah", "diskon", "terlaris", "termurah", "ori", "asli", "promo",
    "the", "and", "for", "with", "of", "to", "at", "in", "by", "on",
    "x", "no",
})

MIN_JACCARD = 0.40
MIN_OVERLAP_TOKENS = 1


def _strip_tokens_for_game(canonical: str) -> set[str]:
    """Return tokens (and singular/plural twins) that identify the game itself."""
    raw = {t for t in re.split(r"[^a-z0-9]+", canonical.lower()) if t}
    out: set[str] = set()
    for t in raw:
        out.add(t)
        if len(t) > 2:
            if t.endswith("s"):
                out.add(t[:-1])
            else:
                out.add(t + "s")
    return out


def tokenize(text: str, game_strip: set[str]) -> set[str]:
    s = (text or "").lower()
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return {
        t for t in s.split()
        if len(t) >= 2 and t not in STOPWORDS and t not in game_strip
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class ItemMatch:
    game: str
    itemku_name: str
    itemku_price_idr: int
    itemku_order_count: int
    g2g_match_count: int
    g2g_min_usd: float
    g2g_median_usd: float
    g2g_avg_usd: float
    g2g_best_title: str
    match_confidence: float


def match_per_game(
    canonical: str,
    itemku_products: Iterable[dict],
    g2g_offers: Iterable[dict],
    *,
    min_jaccard: float = MIN_JACCARD,
    min_overlap: int = MIN_OVERLAP_TOKENS,
) -> list[ItemMatch]:
    """For every Itemku product in this game's bucket, find the best matching
    G2G offers and return arbitrage rows."""
    game_strip = _strip_tokens_for_game(canonical)

    g2g_index: list[tuple[set[str], dict]] = []
    for off in g2g_offers:
        toks = tokenize(off.get("title", ""), game_strip)
        if not toks:
            continue
        price = off.get("unit_price_in_usd")
        if not isinstance(price, (int, float)) or price <= 0:
            continue
        g2g_index.append((toks, off))

    out: list[ItemMatch] = []
    for prod in itemku_products:
        name = prod.get("name") or ""
        price = prod.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            continue
        toks = tokenize(name, game_strip)
        if not toks:
            continue

        candidates: list[tuple[float, dict]] = []
        for g_toks, off in g2g_index:
            common = toks & g_toks
            if len(common) < min_overlap:
                continue
            j = jaccard(toks, g_toks)
            if j < min_jaccard:
                continue
            candidates.append((j, off))

        if not candidates:
            continue

        candidates.sort(key=lambda x: x[0], reverse=True)
        prices_usd = [
            c[1].get("unit_price_in_usd") for c in candidates
            if isinstance(c[1].get("unit_price_in_usd"), (int, float))
            and c[1].get("unit_price_in_usd") > 0
        ]
        if not prices_usd:
            continue

        out.append(ItemMatch(
            game=canonical,
            itemku_name=name,
            itemku_price_idr=int(price),
            itemku_order_count=int(prod.get("order_count") or 0),
            g2g_match_count=len(candidates),
            g2g_min_usd=float(min(prices_usd)),
            g2g_median_usd=float(median(prices_usd)),
            g2g_avg_usd=float(sum(prices_usd) / len(prices_usd)),
            g2g_best_title=str(candidates[0][1].get("title") or "")[:120],
            match_confidence=round(candidates[0][0], 3),
        ))

    return out
