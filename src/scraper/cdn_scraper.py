"""
NBA CDN scraper using plain requests against data.nba.com.

data.nba.com is a CDN with lighter protection than stats.nba.com and responds
to requests with a standard browser User-Agent header — no browser required.

Raw JSON responses are cached under JSON_CACHE_DIR so that re-parsing the data
(e.g. after model changes) does not require re-fetching from the CDN.
"""
import json
import logging
import os

import requests

from src.constants import JSON_CACHE_DIR, NBA_CDN_BASE, NBA_REQUEST_HEADERS

logger = logging.getLogger(__name__)


def _season_year(game_id: str) -> int:
    """Extract the season start year from an NBA game ID (e.g. '0022400455' → 2024)."""
    return 2000 + int(game_id[3:5])


def fetch_pbp(game_id: str, period: int) -> dict:
    """Return the raw 'g' dict for one period's play-by-play."""
    filename = f"{game_id}_{period}_pbp.json"
    cache_path = os.path.join(JSON_CACHE_DIR, filename)
    if os.path.isfile(cache_path):
        logger.debug("Cache hit %s", cache_path)
        with open(cache_path) as f:
            return json.load(f)["g"]

    year = _season_year(game_id)
    url = f"{NBA_CDN_BASE}/{year}/scores/pbp/{filename}"
    logger.debug("GET %s", url)
    resp = requests.get(url, headers=NBA_REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    os.makedirs(JSON_CACHE_DIR, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)
    return data["g"]


def fetch_gamedetail(game_id: str) -> dict:
    """Return the raw 'g' dict from the game-detail endpoint."""
    filename = f"{game_id}_gamedetail.json"
    cache_path = os.path.join(JSON_CACHE_DIR, filename)
    if os.path.isfile(cache_path):
        logger.debug("Cache hit %s", cache_path)
        with open(cache_path) as f:
            return json.load(f)["g"]

    year = _season_year(game_id)
    url = f"{NBA_CDN_BASE}/{year}/scores/gamedetail/{filename}"
    logger.debug("GET %s", url)
    resp = requests.get(url, headers=NBA_REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    os.makedirs(JSON_CACHE_DIR, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f, indent = 2)
    return data["g"]
