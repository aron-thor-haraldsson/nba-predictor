"""
Scrapes and stores all games for one or more NBA seasons.

Games already present on disk (checked via storage.game_exists) are skipped
to avoid redundant API calls.

Game ID lists are cached under SEASONS_DIR as {year}_game_ids.json.
If one is already on disk it is used directly; otherwise it is fetched from
the stats.nba.com leaguegamefinder endpoint and saved for future runs.
"""
import datetime
import json
import logging
import os

import requests

from src.constants import JSON_CACHE_DIR, SEASONS_DIR
from src.models.game import Game
from src.scraper.game_scraper import GameNotPlayedError, scrape_game
from src.scraper.stats_scraper import NBA_STATS_BASE, STATS_HEADERS
from src.scraper.storage import game_exists, load_game, save_game

logger = logging.getLogger(__name__)

_SCRAPEABLE_GAME_TYPES = frozenset("2456")  # regular, playoff, play-in, in-season tournament


def _json_cached(game_id: str) -> bool:
    summary = os.path.join(JSON_CACHE_DIR, f"{game_id}_stats_summary.json")
    pbp = os.path.join(JSON_CACHE_DIR, f"{game_id}_stats_pbp.json")
    return os.path.isfile(summary) and os.path.isfile(pbp)


def _print_game_line(prefix: str, game: Game) -> None:
    final = game.events[-1] if game.events else None
    home_score = final.home_score if final else 0
    away_score = final.away_score if final else 0
    print(
        f"{prefix:<13} [{game.game_id}] {game.date} | "
        f"{game.home_team_abbr} vs {game.away_team_abbr} | "
        f"{home_score}-{away_score} | {len(game.events)} events"
    )


def _game_ids_path(year: int) -> str:
    return os.path.join(SEASONS_DIR, f"{year}_game_ids.json")


def _fetch_game_ids(year: int) -> list[str]:
    """Fetch all completed game IDs for a season from stats.nba.com leaguegamefinder.

    year is the season end year (e.g. 2025 for 2024-25).
    Queries both Regular Season and Playoffs; deduplicates by game ID.
    """
    season_str = f"{year - 1}-{str(year)[-2:]}"
    today = datetime.date.today().isoformat()
    seen: set[str] = set()
    ids: list[str] = []

    for season_type in ("Regular Season", "Playoffs"):
        resp = requests.get(
            f"{NBA_STATS_BASE}/leaguegamefinder",
            headers=STATS_HEADERS,
            params={"Season": season_str, "SeasonType": season_type, "PlayerOrTeam": "T"},
            timeout=60,
        )
        resp.raise_for_status()
        rs = next(
            r for r in resp.json()["resultSets"]
            if r["name"] == "LeagueGameFinderResults"
        )
        h = rs["headers"]
        gid_idx = h.index("GAME_ID")
        date_idx = h.index("GAME_DATE")
        for row in rs["rowSet"]:
            gid = row[gid_idx]
            if gid[2] not in _SCRAPEABLE_GAME_TYPES:
                continue
            if gid in seen:
                continue
            if row[date_idx] > today:
                continue
            seen.add(gid)
            ids.append(gid)

    logger.info("Found %d completed games for %d season", len(ids), year)
    return ids


def _load_game_ids(year: int, force_refresh: bool = False) -> list[str]:
    path = _game_ids_path(year)
    if os.path.isfile(path) and not force_refresh:
        logger.info("Loading %d game IDs from %s", year, path)
        with open(path) as f:
            return json.load(f)
    ids = _fetch_game_ids(year)
    os.makedirs(SEASONS_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(ids, f, indent=2)
    logger.info("Saved %d game IDs to %s", year, path)
    return ids


def scrape_season(year: int, force_refresh: bool = False) -> list[Game]:
    """Scrape all completed games for an NBA season identified by its end year (e.g. 2025)."""
    game_ids = _load_game_ids(year, force_refresh=force_refresh)
    games = []
    for game_id in game_ids:
        if game_exists(game_id):
            game = load_game(game_id)
            logger.debug("Loaded cached game %s", game_id)
            _print_game_line("[pkl cached]", game)
        else:
            prefix = "[half-scrape]" if _json_cached(game_id) else "[scraped]"
            try:
                game = scrape_game(game_id)
            except GameNotPlayedError as e:
                logger.warning("Skipping %s: %s", game_id, e)
                continue
            save_game(game)
            _print_game_line(prefix, game)
        games.append(game)
    return games


def scrape_all_seasons(start_year: int, end_year: int, force_refresh: bool = False) -> list[Game]:
    """Scrape all games across a range of seasons (inclusive end years)."""
    games = []
    for year in range(start_year, end_year + 1):
        games.extend(scrape_season(year, force_refresh=force_refresh))
    return games
