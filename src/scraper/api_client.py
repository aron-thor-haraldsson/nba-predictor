"""
HTTP client for stats.nba.com, covering the 1996-97 season onward.

stats.nba.com enforces stricter bot detection than most public APIs and requires
a full set of modern browser headers (Chrome UA, Referer, Origin, Sec-* fields).

Endpoints used:
  playbyplayv3       — all play-by-play actions for a game; returns {"game": {"actions": [...]}}
  boxscoresummaryv2  — game date, home/visitor team IDs and abbreviations; returns resultSets
  leaguegamefinder   — list of game IDs for a given season (used by season_scraper)
"""
import json
import logging
import os

import requests

from src.constants import JSON_CACHE_DIR

logger = logging.getLogger(__name__)

NBA_STATS_BASE = "https://stats.nba.com/stats"
# A modern Chrome User-Agent plus the full set of expected CORS/Sec-* headers is required;
# a plain or outdated UA causes a read timeout.
STATS_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def rowset_to_dicts(result_set: dict) -> list[dict]:
    headers = result_set["headers"]
    return [dict(zip(headers, row)) for row in result_set["rowSet"]]


def _find_result_set(result_sets: list[dict], name: str) -> dict:
    for rs in result_sets:
        if rs["name"] == name:
            return rs
    raise ValueError(f"Result set '{name}' not found in response")


def fetch_stats_summary(game_id: str) -> dict:
    """Return game metadata from stats.nba.com boxscoresummaryv2.

    Result: {game_id, game_date_est, home_team_id, home_team_abbr,
              visitor_team_id, visitor_team_abbr}
    """
    filename = f"{game_id}_stats_summary.json"
    cache_path = os.path.join(JSON_CACHE_DIR, filename)
    if os.path.isfile(cache_path):
        logger.debug("Cache hit %s", filename)
        with open(cache_path) as f:
            return json.load(f)

    url = f"{NBA_STATS_BASE}/boxscoresummaryv2"
    logger.debug("GET %s?GameID=%s", url, game_id)
    resp = requests.get(url, headers=STATS_HEADERS, params={"GameID": game_id}, timeout=60)
    resp.raise_for_status()
    result_sets = resp.json()["resultSets"]

    game_summary = rowset_to_dicts(_find_result_set(result_sets, "GameSummary"))[0]
    linescore_rows = rowset_to_dicts(_find_result_set(result_sets, "LineScore"))

    home_team_id = int(game_summary["HOME_TEAM_ID"])
    visitor_team_id = int(game_summary["VISITOR_TEAM_ID"])
    # GAME_DATE_EST may include a time component ("2025-01-02T00:00:00"); take the date only
    game_date_est = str(game_summary["GAME_DATE_EST"])[:10]

    team_id_to_abbr = {int(r["TEAM_ID"]): r["TEAM_ABBREVIATION"] for r in linescore_rows}

    summary = {
        "game_id": game_id,
        "game_date_est": game_date_est,
        "home_team_id": home_team_id,
        "home_team_abbr": team_id_to_abbr[home_team_id],
        "visitor_team_id": visitor_team_id,
        "visitor_team_abbr": team_id_to_abbr[visitor_team_id],
    }
    os.makedirs(JSON_CACHE_DIR, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def fetch_stats_pbp(game_id: str) -> list[dict]:
    """Return all play-by-play actions from stats.nba.com playbyplayv3 (all periods).

    Each action is a dict with fields: actionNumber, clock (ISO 8601 "PT12M00.00S"),
    period, teamId, teamTricode, personId, playerName, actionType, subType,
    description, scoreHome, scoreAway, isFieldGoal, ...
    Empty responses are not cached so a retry will re-fetch.
    """
    filename = f"{game_id}_stats_pbp.json"
    cache_path = os.path.join(JSON_CACHE_DIR, filename)
    if os.path.isfile(cache_path):
        logger.debug("Cache hit %s", filename)
        with open(cache_path) as f:
            return json.load(f)

    url = f"{NBA_STATS_BASE}/playbyplayv3"
    params = {"GameID": game_id, "StartPeriod": 0, "EndPeriod": 0}
    logger.debug("GET %s?GameID=%s", url, game_id)
    resp = requests.get(url, headers=STATS_HEADERS, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "game" not in data:
        logger.error(
            "Unexpected stats.nba.com/playbyplayv3 response for %s: top-level keys=%s",
            game_id, list(data.keys()),
        )
        raise ValueError(
            f"Unrecognized playbyplayv3 response for {game_id}: keys={list(data.keys())}"
        )
    actions = data["game"].get("actions", [])

    if not actions:
        return actions  # don't cache empty responses — game may not have data yet
    os.makedirs(JSON_CACHE_DIR, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(actions, f, indent=2)
    return actions
