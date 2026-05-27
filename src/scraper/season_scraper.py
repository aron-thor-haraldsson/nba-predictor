"""
Scrapes and stores all games for one or more NBA seasons.

Games already present on disk (checked via storage.game_exists) are skipped
to avoid redundant API calls.

Schedule JSON files are cached under SEASONS_DIR as {year}_schedule.json.
If one is already on disk it is used directly; otherwise it is fetched from
the NBA schedule endpoint and saved for future runs.
"""
import datetime
import json
import logging
import os

import requests

from src.constants import NBA_CDN_BASE, NBA_REQUEST_HEADERS, SEASONS_DIR
from src.models.game import Game
from src.scraper.game_scraper import GameNotPlayedError, scrape_game
from src.scraper.storage import game_exists, load_game, save_game

logger = logging.getLogger(__name__)


def _schedule_path(year: int) -> str:
    return os.path.join(SEASONS_DIR, f"{year}_schedule.json")


def _load_schedule(year: int, force_refresh: bool = False) -> dict:
    path = _schedule_path(year)
    if os.path.isfile(path) and not force_refresh:
        logger.info("Loading %d schedule from %s", year, path)
        with open(path) as f:
            return json.load(f)
    url = f"{NBA_CDN_BASE}/{year}/league/00_full_schedule.json"
    logger.info("Fetching %d schedule from %s", year, url)
    resp = requests.get(url, headers=NBA_REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    os.makedirs(SEASONS_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Saved %d schedule to %s", year, path)
    return data


_SCRAPEABLE_GAME_TYPES = frozenset("2456")  # regular, playoff, play-in, in-season tournament


def _completed_game_ids(schedule: dict) -> list[str]:
    today = datetime.date.today().isoformat()
    ids = []
    for month in schedule["lscd"]:
        for game in month["mscd"]["g"]:
            if game["gid"][2] not in _SCRAPEABLE_GAME_TYPES:
                continue
            if game.get("st") == "3" or game.get("gdte", "") < today:
                ids.append(game["gid"])
    return ids


def scrape_season(year: int, force_refresh: bool = False) -> list[Game]:
    """Scrape all completed games for an NBA season identified by its end year (e.g. 2025)."""
    schedule = _load_schedule(year, force_refresh=force_refresh)
    game_ids = _completed_game_ids(schedule)
    logger.info("Found %d completed games for %d season", len(game_ids), year)
    games = []
    for game_id in game_ids:
        if game_exists(game_id):
            game = load_game(game_id)
            logger.debug("Loaded cached game %s", game_id)
        else:
            try:
                game = scrape_game(game_id)
            except GameNotPlayedError as e:
                logger.warning("Skipping %s: %s", game_id, e)
                continue
            save_game(game)
        games.append(game)
    return games


def scrape_all_seasons(start_year: int, end_year: int, force_refresh: bool = False) -> list[Game]:
    """Scrape all games across a range of seasons (inclusive end years)."""
    games = []
    for year in range(start_year, end_year + 1):
        games.extend(scrape_season(year, force_refresh=force_refresh))
    return games
