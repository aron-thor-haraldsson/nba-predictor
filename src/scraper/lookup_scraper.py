"""
Fetches and caches player and team lookup tables from stats.nba.com.

Players: commonallplayers (all historical, ~5000+ entries)
Teams:   franchisehistory + commonteamyears (30 active franchises)

Usage (always force-refreshes from the API):
  python -m src.scraper.lookup_scraper --fetch_players
  python -m src.scraper.lookup_scraper --fetch_teams
  python -m src.scraper.lookup_scraper --fetch_teams_history
  python -m src.scraper.lookup_scraper --fetch_all_lookup
"""
import argparse
import csv
import logging
import os
from collections import defaultdict

import requests

from src.constants import PLAYERS_CSV, TEAMS_HISTORY_CSV, TEAMS_CSV
from src.scraper.api_client import NBA_STATS_BASE, STATS_HEADERS, rowset_to_dicts

logger = logging.getLogger(__name__)

_PLAYER_FIELDS = ["person_id", "player_name", "player_name_i", "full_name"]
_TEAM_FIELDS = ["team_id", "team_tricode", "team_full_name"]
_TEAMS_HISTORY_FIELDS = ["team_id", "team_city", "team_name", "start_year", "end_year"]



def fetch_players(force_refresh: bool = False) -> list[dict]:
    """Return all historical NBA players.

    Each entry has: person_id (int), player_name (last name), player_name_i
    (initial + last name, e.g. "J. Hayes"), full_name.
    Results are cached to PLAYERS_CSV; pass force_refresh=True to re-fetch.
    """
    if os.path.isfile(PLAYERS_CSV) and not force_refresh:
        logger.debug("Cache hit %s", PLAYERS_CSV)
        return _load_players()

    resp = requests.get(
        f"{NBA_STATS_BASE}/commonallplayers",
        headers=STATS_HEADERS,
        params={"LeagueID": "00", "Season": "2024-25", "IsOnlyCurrentSeason": "0"},
        timeout=60,
    )
    resp.raise_for_status()
    rows = rowset_to_dicts(resp.json()["resultSets"][0])

    players = []
    for r in rows:
        raw = r.get("DISPLAY_LAST_COMMA_FIRST") or ""
        last_name = raw.split(", ")[0] if ", " in raw else raw
        full_name = r.get("DISPLAY_FIRST_LAST") or ""
        player_name_i = (full_name[0] + ". " + last_name) if full_name and last_name else ""
        players.append({
            "person_id": r["PERSON_ID"],
            "player_name": last_name,
            "player_name_i": player_name_i,
            "full_name": full_name,
        })

    _save_players(players)
    logger.info("Fetched %d players → %s", len(players), PLAYERS_CSV)
    return players


def fetch_teams(force_refresh: bool = False) -> list[dict]:
    """Return all 30 active NBA franchises.

    Each entry has: team_id (int), team_tricode, team_full_name (city + name).
    Uses the most recently active city/name for franchises that have relocated.
    Results are cached to TEAMS_CSV; pass force_refresh=True to re-fetch.
    """
    if os.path.isfile(TEAMS_CSV) and not force_refresh:
        logger.debug("Cache hit %s", TEAMS_CSV)
        return _load_teams()

    resp = requests.get(
        f"{NBA_STATS_BASE}/franchisehistory",
        headers=STATS_HEADERS,
        params={"LeagueID": "00"},
        timeout=60,
    )
    resp.raise_for_status()
    active_rows = rowset_to_dicts(resp.json()["resultSets"][0])  # FranchiseHistory

    by_id: dict[int, list[dict]] = defaultdict(list)
    for r in active_rows:
        by_id[r["TEAM_ID"]].append(r)

    latest_name: dict[int, str] = {
        team_id: f"{max(rows, key=lambda r: r['END_YEAR'])['TEAM_CITY']} "
                 f"{max(rows, key=lambda r: r['END_YEAR'])['TEAM_NAME']}"
        for team_id, rows in by_id.items()
    }

    resp2 = requests.get(
        f"{NBA_STATS_BASE}/commonteamyears",
        headers=STATS_HEADERS,
        params={"LeagueID": "00"},
        timeout=60,
    )
    resp2.raise_for_status()
    tricode_by_id = {
        r["TEAM_ID"]: r["ABBREVIATION"]
        for r in rowset_to_dicts(resp2.json()["resultSets"][0])
        if r["ABBREVIATION"]
    }

    teams = [
        {
            "team_id": team_id,
            "team_tricode": tricode_by_id[team_id],
            "team_full_name": full_name,
        }
        for team_id, full_name in sorted(latest_name.items())
        if team_id in tricode_by_id
    ]

    _save_teams(teams)
    logger.info("Fetched %d teams → %s", len(teams), TEAMS_CSV)
    return teams


def _save_players(players: list[dict]) -> None:
    os.makedirs(os.path.dirname(PLAYERS_CSV), exist_ok=True)
    with open(PLAYERS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_PLAYER_FIELDS)
        writer.writeheader()
        writer.writerows(players)


def _load_players() -> list[dict]:
    with open(PLAYERS_CSV, newline="") as f:
        return [{**r, "person_id": int(r["person_id"])} for r in csv.DictReader(f)]


def _save_teams(teams: list[dict]) -> None:
    os.makedirs(os.path.dirname(TEAMS_CSV), exist_ok=True)
    with open(TEAMS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TEAM_FIELDS)
        writer.writeheader()
        writer.writerows(teams)


def _load_teams() -> list[dict]:
    with open(TEAMS_CSV, newline="") as f:
        return [{**r, "team_id": int(r["team_id"])} for r in csv.DictReader(f)]


def fetch_teams_history(force_refresh: bool = False) -> list[dict]:
    """Return one row per franchise era for all 30 active NBA franchises.

    Each entry has: team_id (int), team_city, team_name, start_year (int),
    end_year (int). start_year/end_year are the first year of the NBA season
    (e.g. 2008 = 2008-09). A franchise that changed city or name produces
    multiple rows with the same team_id.
    Results are cached to TEAMS_HISTORY_CSV; pass force_refresh=True to re-fetch.
    """
    if os.path.isfile(TEAMS_HISTORY_CSV) and not force_refresh:
        logger.debug("Cache hit %s", TEAMS_HISTORY_CSV)
        return _load_teams_history()

    resp = requests.get(
        f"{NBA_STATS_BASE}/franchisehistory",
        headers=STATS_HEADERS,
        params={"LeagueID": "00"},
        timeout=60,
    )
    resp.raise_for_status()
    raw_rows = rowset_to_dicts(resp.json()["resultSets"][0])  # active franchises only

    history = [
        {
            "team_id": r["TEAM_ID"],
            "team_city": r["TEAM_CITY"],
            "team_name": r["TEAM_NAME"],
            "start_year": r["START_YEAR"],
            "end_year": r["END_YEAR"],
        }
        for r in raw_rows
    ]

    _save_teams_history(history)
    logger.info("Fetched %d franchise eras → %s", len(history), TEAMS_HISTORY_CSV)
    return _load_teams_history()


def _save_teams_history(history: list[dict]) -> None:
    os.makedirs(os.path.dirname(TEAMS_HISTORY_CSV), exist_ok=True)
    with open(TEAMS_HISTORY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TEAMS_HISTORY_FIELDS)
        writer.writeheader()
        writer.writerows(history)


def _load_teams_history() -> list[dict]:
    with open(TEAMS_HISTORY_CSV, newline="") as f:
        return [
            {**r, "team_id": int(r["team_id"]), "start_year": int(r["start_year"]), "end_year": int(r["end_year"])}
            for r in csv.DictReader(f)
        ]


if __name__ == "__main__":
    from src.logging_config import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Refresh lookup tables from stats.nba.com.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fetch_players", action="store_true")
    group.add_argument("--fetch_teams", action="store_true")
    group.add_argument("--fetch_teams_history", action="store_true")
    group.add_argument("--fetch_all_lookup", action="store_true")
    args = parser.parse_args()

    if args.fetch_players or args.fetch_all_lookup:
        fetch_players(force_refresh=True)
    if args.fetch_teams or args.fetch_all_lookup:
        fetch_teams(force_refresh=True)
    if args.fetch_teams_history or args.fetch_all_lookup:
        fetch_teams_history(force_refresh=True)
