"""
Fetches play-by-play data and converts it into the project's Game datatype.

Primary source: data.nba.com CDN (fast, cached JSON, lighter bot protection).
Fallback source: stats.nba.com (used when the CDN has not yet archived a game).

API calls are expensive; always check storage.game_exists() before scraping.
"""
import datetime
import logging

import requests

from src.models.game import Game, PlayByPlayEvent
from src.scraper.cdn_scraper import fetch_gamedetail, fetch_pbp
from src.scraper.stats_scraper import fetch_stats_pbp, fetch_stats_summary

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


def _parse_iso_clock(clock: str) -> str:
    """Convert playbyplayv3 ISO 8601 clock 'PT12M30.00S' → '12:30.0'."""
    inner = clock[2:-1]  # strip leading "PT" and trailing "S" → "12M30.00"
    minutes_str, seconds_str = inner.split("M")
    minutes = int(minutes_str)
    sec_int, _, frac = seconds_str.partition(".")
    tenths = frac[0] if frac else "0"
    return f"{minutes}:{int(sec_int):02d}.{tenths}"


def _v3_event_type(action_type: str, sub_type: str, description: str) -> str:
    """Map playbyplayv3 actionType → our event_type string."""
    match action_type:
        case "2pt" | "3pt":
            return "missed_field_goal" if "MISS" in description.upper() else "field_goal"
        case "freethrow":
            return "free_throw"
        case "rebound":
            return "rebound"
        case "turnover":
            return "turnover"
        case "foul":
            return "foul"
        case "violation":
            return "violation"
        case "substitution":
            return "substitution"
        case "timeout":
            return "timeout"
        case "jumpball":
            return "jump_ball"
        case "period":
            return "end_period" if sub_type == "end" else "start_period"
        case _:
            return action_type


def _infer_starters_stats(
    period1_actions: list[dict],
    pid_to_team: dict[int, str],
    pid_to_name: dict[int, str],
    home_abbr: str,
    away_abbr: str,
) -> tuple[list[str], list[str]]:
    """Return [home_starters], [away_starters] inferred from period-1 playbyplayv3 actions."""
    sentinel = len(period1_actions)
    first_sub: dict[str, int] = {home_abbr: sentinel, away_abbr: sentinel}
    for i, action in enumerate(period1_actions):
        if action.get("actionType") == "substitution" and action.get("subType") == "out":
            team = action.get("teamTricode", "")
            if team in first_sub and first_sub[team] == sentinel:
                first_sub[team] = i

    home: list[str] = []
    away: list[str] = []
    for i, action in enumerate(period1_actions):
        if len(home) >= 5 and len(away) >= 5:
            break
        pid = int(action.get("personId") or 0)
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


def _build_game_from_stats(summary: dict, actions: list[dict]) -> Game:
    """Build a Game from stats.nba.com playbyplayv3 actions + boxscoresummaryv2 summary.

    playbyplayv3 substitution events come as separate "out" + "in" action pairs.
    Scores are in scoreHome / scoreAway string fields on every action.
    Clock is ISO 8601: "PT12M00.00S".
    """
    home_abbr: str = summary["home_team_abbr"]
    away_abbr: str = summary["visitor_team_abbr"]
    game_id: str = summary["game_id"]
    game_date = datetime.date.fromisoformat(summary["game_date_est"])

    # Build player maps from all actions (covers bench players who only appear in subs)
    pid_to_name: dict[int, str] = {}
    pid_to_team: dict[int, str] = {}
    for action in actions:
        pid = int(action.get("personId") or 0)
        name = action.get("playerName") or ""
        team = action.get("teamTricode") or ""
        if pid > 0 and name and team:
            pid_to_name[pid] = name
            pid_to_team[pid] = team

    period1_actions = [a for a in actions if int(a.get("period") or 0) == 1]
    home_lineup, away_lineup = _infer_starters_stats(
        period1_actions, pid_to_team, pid_to_name, home_abbr, away_abbr
    )

    # v3 substitutions come as separate "out" then "in" events; pair them by team
    pending_out: dict[str, int] = {}  # teamTricode → outgoing personId
    events: list[PlayByPlayEvent] = []

    for action in actions:
        action_type = action.get("actionType", "")
        sub_type = action.get("subType", "")
        pid = int(action.get("personId") or 0)
        team = action.get("teamTricode") or ""

        if action_type == "substitution":
            if sub_type == "out":
                pending_out[team] = pid
            elif sub_type == "in" and team in pending_out:
                out_pid = pending_out.pop(team)
                name_out = pid_to_name.get(out_pid)
                name_in = pid_to_name.get(pid)
                if name_out and name_in:
                    if team == home_abbr:
                        home_lineup = [name_in if n == name_out else n for n in home_lineup]
                    elif team == away_abbr:
                        away_lineup = [name_in if n == name_out else n for n in away_lineup]

        clock = _parse_iso_clock(action.get("clock") or "PT00M00.00S")
        desc = action.get("description") or ""
        home_score = int(action.get("scoreHome") or 0)
        away_score = int(action.get("scoreAway") or 0)

        events.append(PlayByPlayEvent(
            period=int(action["period"]),
            clock=clock,
            event_type=_v3_event_type(action_type, sub_type, desc),
            description=desc,
            home_score=home_score,
            away_score=away_score,
            home_players=tuple(home_lineup),
            away_players=tuple(away_lineup),
        ))

    final = events[-1] if events else None
    logger.info(
        "Built game %s (stats.nba.com): %d events, %s %d – %d %s",
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


def _scrape_game_from_stats(game_id: str) -> Game:
    try:
        summary = fetch_stats_summary(game_id)
        pbp_rows = fetch_stats_pbp(game_id)
    except requests.HTTPError as e:
        raise GameNotPlayedError(
            f"Game {game_id} unavailable on CDN and stats.nba.com"
        ) from e
    if not pbp_rows:
        raise GameNotPlayedError(f"Game {game_id} has no play-by-play data on stats.nba.com")
    return _build_game_from_stats(summary, pbp_rows)


class GameNotPlayedError(Exception):
    pass


def scrape_game(game_id: str) -> Game:
    """Fetch play-by-play data for a single game and return a Game object.

    Tries data.nba.com CDN first; falls back to stats.nba.com when the CDN has not
    yet archived the game (typical for the current season).
    Raises GameNotPlayedError if neither source has data (postponed/cancelled game).
    """
    logger.info("Scraping game %s", game_id)
    gamedetail = fetch_gamedetail(game_id)

    if gamedetail.get("p"):
        num_periods = max(4, int(gamedetail["p"]))
        try:
            periods_pbp = [fetch_pbp(game_id, p)["pla"] for p in range(1, num_periods + 1)]
            if any(periods_pbp):
                return _build_game(gamedetail, periods_pbp)
        except requests.HTTPError:
            pass
        logger.info("CDN PBP empty for %s, falling back to stats.nba.com", game_id)
    else:
        logger.info("CDN has no data for %s, falling back to stats.nba.com", game_id)

    return _scrape_game_from_stats(game_id)
