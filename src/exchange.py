"""USD <-> IDR exchange rate helper.

Itemku's `exchangeRate` is locked to the visitor's region (always IDR->IDR=1
for Indonesian IPs / cookies), so we use a free public rate service instead.
"""
from __future__ import annotations

import os
import requests

DEFAULT_FALLBACK_RATE = 16500.0   # rough USD/IDR if everything else fails
ENV_OVERRIDE = "USD_IDR_RATE"
RATE_URL = "https://open.er-api.com/v6/latest/USD"
TIMEOUT = 10


def fetch_usd_to_idr() -> float:
    """Return live USD->IDR rate. Order: env override > public API > fallback."""
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        try:
            return float(override)
        except ValueError:
            pass
    try:
        r = requests.get(RATE_URL, timeout=TIMEOUT)
        r.raise_for_status()
        rate = r.json().get("rates", {}).get("IDR")
        if isinstance(rate, (int, float)) and rate > 0:
            return float(rate)
    except Exception:
        pass
    return DEFAULT_FALLBACK_RATE
