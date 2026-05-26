"""
NBA CDN scraper using plain requests against data.nba.com.

data.nba.com is a CDN with lighter protection than stats.nba.com and responds
to requests with a standard browser User-Agent header — no browser required.
"""
import logging

import requests

from src.constants import NBA_CDN_BASE, NBA_REQUEST_HEADERS

logger = logging.getLogger(__name__)


def _season_year(game_id: str) -> int:
    """Extract the season start year from an NBA game ID (e.g. '0022400455' → 2024)."""
    return 2000 + int(game_id[3:5])


def fetch_pbp(game_id: str, period: int) -> dict:
    """Return the raw 'g' dict for one period's play-by-play."""
    year = _season_year(game_id)
    url = f"{NBA_CDN_BASE}/{year}/scores/pbp/{game_id}_{period}_pbp.json"
    logger.debug("GET %s", url)
    resp = requests.get(url, headers=NBA_REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["g"]


def fetch_gamedetail(game_id: str) -> dict:
    """Return the raw 'g' dict from the game-detail endpoint."""
    year = _season_year(game_id)
    url = f"{NBA_CDN_BASE}/{year}/scores/gamedetail/{game_id}_gamedetail.json"
    logger.debug("GET %s", url)
    resp = requests.get(url, headers=NBA_REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["g"]
