"""Roblox popular-games collector.

Strategy: hit the public Explore API (no auth) which powers roblox.com/charts.
It returns several sort buckets (top-trending, top-playing-now, up-and-coming,
fun-with-friends, top-revisited) — we flatten them, dedupe by universeId,
and keep the highest player_count seen.

Optionally enrich with `games?universeIds=...` for visits/favorites/creator.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Iterable

import requests

EXPLORE_SORTS_URL = "https://apis.roblox.com/explore-api/v1/get-sorts"
GAMES_DETAILS_URL = "https://games.roblox.com/v1/games"
GAMES_VOTES_URL = "https://games.roblox.com/v1/games/votes"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "g2g-roblox-bot/0.1 (research; contact via repo)",
}
DETAILS_BATCH_SIZE = 50
REQUEST_TIMEOUT = 20


@dataclass
class RobloxGame:
    universe_id: int
    place_id: int
    name: str
    ccu: int
    upvotes: int = 0
    downvotes: int = 0
    min_age: int = 0
    sort_sources: list[str] = field(default_factory=list)
    visits: int = 0
    favorites: int = 0
    creator_name: str = ""
    creator_type: str = ""
    description: str = ""

    @property
    def rating(self) -> float:
        total = self.upvotes + self.downvotes
        return self.upvotes / total if total else 0.0

    @property
    def roblox_url(self) -> str:
        return f"https://www.roblox.com/games/{self.place_id}/"

    def to_dict(self) -> dict:
        return {
            "universe_id": self.universe_id,
            "place_id": self.place_id,
            "name": self.name,
            "ccu": self.ccu,
            "upvotes": self.upvotes,
            "downvotes": self.downvotes,
            "rating": round(self.rating, 4),
            "min_age": self.min_age,
            "sort_sources": self.sort_sources,
            "visits": self.visits,
            "favorites": self.favorites,
            "creator_name": self.creator_name,
            "creator_type": self.creator_type,
            "roblox_url": self.roblox_url,
        }


def _new_session_id() -> str:
    return str(uuid.uuid4())


def fetch_sorts(session_id: str | None = None) -> list[dict]:
    params = {
        "sessionId": session_id or _new_session_id(),
        "sortsPageToken": "",
    }
    r = requests.get(
        EXPLORE_SORTS_URL,
        params=params,
        headers=DEFAULT_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("sorts", [])


def collect_popular_games(min_ccu: int = 0) -> list[RobloxGame]:
    """Flatten all sort buckets into a deduped list. Highest CCU wins on dupes."""
    by_universe: dict[int, RobloxGame] = {}
    for sort in fetch_sorts():
        sort_id = sort.get("sortId", "")
        for raw in sort.get("games", []):
            universe_id = raw.get("universeId")
            place_id = raw.get("rootPlaceId")
            if not universe_id or not place_id:
                continue
            ccu = raw.get("playerCount", 0) or 0
            if ccu < min_ccu:
                continue
            existing = by_universe.get(universe_id)
            if existing is None:
                by_universe[universe_id] = RobloxGame(
                    universe_id=universe_id,
                    place_id=place_id,
                    name=raw.get("name", "").strip(),
                    ccu=ccu,
                    upvotes=raw.get("totalUpVotes", 0) or 0,
                    downvotes=raw.get("totalDownVotes", 0) or 0,
                    min_age=raw.get("minimumAge", 0) or 0,
                    sort_sources=[sort_id],
                )
            else:
                if ccu > existing.ccu:
                    existing.ccu = ccu
                if sort_id and sort_id not in existing.sort_sources:
                    existing.sort_sources.append(sort_id)
    return sorted(by_universe.values(), key=lambda g: g.ccu, reverse=True)


def _chunked(seq: list[int], size: int) -> Iterable[list[int]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def enrich_with_details(games: list[RobloxGame]) -> list[RobloxGame]:
    """Fill visits/favorites/creator/description by batch-querying games endpoint."""
    by_id = {g.universe_id: g for g in games}
    for batch in _chunked(list(by_id.keys()), DETAILS_BATCH_SIZE):
        ids_csv = ",".join(str(i) for i in batch)
        r = requests.get(
            GAMES_DETAILS_URL,
            params={"universeIds": ids_csv},
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json().get("data", []):
            uid = item.get("id")
            g = by_id.get(uid)
            if not g:
                continue
            g.visits = item.get("visits", 0) or 0
            g.favorites = item.get("favoritedCount", 0) or 0
            creator = item.get("creator") or {}
            g.creator_name = creator.get("name", "") or ""
            g.creator_type = creator.get("type", "") or ""
            g.description = (item.get("description") or "")[:500]
        time.sleep(0.3)  # gentle pacing between batches
    return games
