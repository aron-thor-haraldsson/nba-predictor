"""
Fetches play-by-play data from the NBA CDN and converts it into the
project's Game datatype.

API calls are expensive; always check storage.game_exists() before scraping.
"""
import datetime
import logging

import requests

from src.models.game import Game, PlayByPlayEvent
from src.scraper.cdn_scraper import fetch_gamedetail, fetch_pbp

logger = logging.getLogger(__name__)

_ETYPE_NAMES: dict[int, str] = {
    1: "field_goal",
    2: "missed_field_goal",
    3: "free_throw",
    4: "rebound",
    5: "turnover",
    6: "foul",
    7: "violation",
    8: "substitution",
    9: "timeout",
    10: "jump_ball",
    12: "start_period",
    13: "end_period",
}


def _pid(value) -> int:
    """Safely coerce a player-ID field to int; 0 means 'no player' in CDN data."""
    try:
        return int(value) if value else 0
    except (ValueError, TypeError):
        return 0


def _infer_starters(
    period1_events: list[dict],
    pid_to_team: dict[int, str],
    pid_to_name: dict[int, str],
    home_abbr: str,
    away_abbr: str,
) -> tuple[list[str], list[str]]:
    """Return [home_starters], [away_starters] inferred from period-1 events.

    Collects player names from events that precede each team's first
    substitution, which are guaranteed to be the opening-lineup players.
    """
    sentinel = len(period1_events)
    first_sub: dict[str, int] = {home_abbr: sentinel, away_abbr: sentinel}
    for i, ev in enumerate(period1_events):
        if ev["etype"] == 8:
            team = pid_to_team.get(_pid(ev.get("pid")))
            if team and first_sub[team] == sentinel:
                first_sub[team] = i

    home: list[str] = []
    away: list[str] = []
    for i, ev in enumerate(period1_events):
        if len(home) >= 5 and len(away) >= 5:
            break
        for key in ("pid", "epid", "opid"):  # primary player, entering player (sub), other player (jump ball)
            pid = _pid(ev.get(key))
            if pid <= 0:
                continue
            team = pid_to_team.get(pid)
            name = pid_to_name.get(pid)
            if not name:
                continue
            if team == home_abbr and i < first_sub[home_abbr] and name not in home and len(home) < 5:
                home.append(name)
            elif team == away_abbr and i < first_sub[away_abbr] and name not in away and len(away) < 5:
                away.append(name)

    return home, away


def _build_game(gamedetail: dict, periods_pbp: list[list[dict]]) -> Game:
    home = gamedetail["hls"]
    away = gamedetail["vls"]
    home_abbr: str = home["ta"]
    away_abbr: str = away["ta"]

    pid_to_team: dict[int, str] = {}
    pid_to_name: dict[int, str] = {}
    for player in home["pstsg"]:
        pid_to_team[player["pid"]] = home_abbr
        pid_to_name[player["pid"]] = f"{player['fn']} {player['ln']}"
    for player in away["pstsg"]:
        pid_to_team[player["pid"]] = away_abbr
        pid_to_name[player["pid"]] = f"{player['fn']} {player['ln']}"

    home_lineup, away_lineup = _infer_starters(
        periods_pbp[0], pid_to_team, pid_to_name, home_abbr, away_abbr
    )

    game_date = datetime.date.fromisoformat(gamedetail["gdte"])
    game_id: str = gamedetail["gid"]

    events: list[PlayByPlayEvent] = []
    for period_num, period_events in enumerate(periods_pbp, start=1):
        for ev in period_events:
            etype: int = ev["etype"]

            if etype == 8:
                name_out = pid_to_name.get(_pid(ev.get("pid")))
                name_in = pid_to_name.get(_pid(ev.get("epid")))
                team = pid_to_team.get(_pid(ev.get("pid")))
                if name_out and name_in:
                    if team == home_abbr:
                        home_lineup = [name_in if n == name_out else n for n in home_lineup]
                    elif team == away_abbr:
                        away_lineup = [name_in if n == name_out else n for n in away_lineup]

            clock = ev["cl"]
            if "." not in clock:
                clock += ".0"  # CDN omits the decimal for whole-second clocks above 1 minute
            events.append(PlayByPlayEvent(
                period=period_num,
                clock=clock,
                event_type=_ETYPE_NAMES.get(etype, str(etype)),
                description=ev["de"],
                home_score=ev["hs"],
                away_score=ev["vs"],
                home_players=tuple(home_lineup),
                away_players=tuple(away_lineup),
            ))

    final = events[-1] if events else None
    logger.info(
        "Built game %s: %d events, %s %d – %d %s",
        game_id, len(events),
        home_abbr, final.home_score if final else 0,
        final.away_score if final else 0, away_abbr,
    )
    return Game(
        game_id=game_id,
        date=game_date,
        home_team_abbr=home_abbr,
        away_team_abbr=away_abbr,
        events=events,
    )


class GameNotPlayedError(Exception):
    pass


def scrape_game(game_id: str) -> Game:
    """Fetch play-by-play data for a single game and return a Game object.

    Raises GameNotPlayedError if the CDN has no game data (postponed/cancelled games).
    """
    logger.info("Scraping game %s", game_id)
    gamedetail = fetch_gamedetail(game_id)
    if not gamedetail.get("p"):
        raise GameNotPlayedError(f"Game {game_id} has no period data — likely postponed")
    num_periods = max(4, int(gamedetail["p"]))
    try:
        periods_pbp = [fetch_pbp(game_id, p)["pla"] for p in range(1, num_periods + 1)]
    except requests.HTTPError as e:
        raise GameNotPlayedError(f"Game {game_id} PBP unavailable: {e}") from e
    return _build_game(gamedetail, periods_pbp)
