"""
Fetches play-by-play data and converts it into the project's Game datatype.

Source: stats.nba.com playbyplayv3 + boxscoresummaryv2, covering the 1996-97 season onward.
"""
import datetime
import logging

import requests

from src.models.game import Game, PlayByPlayEvent
from src.scraper.api_client import fetch_stats_pbp, fetch_stats_summary

logger = logging.getLogger(__name__)


def _parse_iso_clock(clock: str) -> str:
    """Convert playbyplayv3 ISO 8601 clock 'PT12M30.00S' → '12:30.0'."""
    inner = clock[2:-1]  # strip leading "PT" and trailing "S"
    minutes_str, seconds_str = inner.split("M")
    minutes = int(minutes_str)
    sec_int, _, frac = seconds_str.partition(".")
    tenths = frac[0] if frac else "0"
    return f"{minutes}:{int(sec_int):02d}.{tenths}"


def _v3_event_type(action_type: str, sub_type: str, description: str) -> str:
    """Map playbyplayv3 actionType → our event_type string."""
    match action_type:
        case "Made Shot":
            return "field_goal"
        case "Missed Shot":
            return "missed_field_goal"
        case "Free Throw":
            return "free_throw"
        case "Rebound":
            return "rebound"
        case "Turnover":
            return "turnover"
        case "Foul":
            return "foul"
        case "Violation":
            return "violation"
        case "Substitution":
            return "substitution"
        case "Timeout":
            return "timeout"
        case "Jump Ball":
            return "jump_ball"
        case "period":
            return "end_period" if sub_type == "end" else "start_period"
        case _:
            return action_type.lower().replace(" ", "_") if action_type else "unknown"


def _parse_sub_description(
    desc: str,
    team: str,
    pid_to_name: dict[int, str],
    pid_to_team: dict[int, str],
) -> tuple[str, int] | None:
    """Extract the incoming player's name and personId from a 'SUB: X FOR Y' description.

    Matches the name fragment against pid_to_name (built from all game actions, so
    bench players who appear later are already registered). Ambiguous fragments will
    match the first player found on the team; this is reliable in practice because
    the NBA does not roster two players with the same last name on the same team.
    Returns (player_name, person_id) or None if no match.
    """
    if "SUB:" not in desc or " FOR " not in desc:
        return None
    fragment = desc.split("SUB:")[1].split(" FOR ")[0].strip()
    for pid, name in pid_to_name.items():
        if pid_to_team.get(pid) == team and fragment in name:
            return name, pid
    return None


def _infer_starters_stats(
    period1_actions: list[dict],
    pid_to_team: dict[int, str],
    pid_to_name: dict[int, str],
    home_abbr: str,
    away_abbr: str,
) -> tuple[list[str], list[int], list[str], list[int]]:
    """Return (home_names, home_ids, away_names, away_ids) inferred from period-1 actions."""
    sentinel = len(period1_actions)
    first_sub: dict[str, int] = {home_abbr: sentinel, away_abbr: sentinel}
    for i, action in enumerate(period1_actions):
        if action.get("actionType") == "Substitution":
            team = action.get("teamTricode", "")
            if team in first_sub and first_sub[team] == sentinel:
                first_sub[team] = i

    home_names: list[str] = []
    home_ids: list[int] = []
    away_names: list[str] = []
    away_ids: list[int] = []
    for i, action in enumerate(period1_actions):
        if len(home_names) >= 5 and len(away_names) >= 5:
            break
        pid = int(action.get("personId") or 0)
        if pid <= 0:
            continue
        team = pid_to_team.get(pid)
        name = pid_to_name.get(pid)
        if not name:
            continue
        if team == home_abbr and i < first_sub[home_abbr] and name not in home_names and len(home_names) < 5:
            home_names.append(name)
            home_ids.append(pid)
        elif team == away_abbr and i < first_sub[away_abbr] and name not in away_names and len(away_names) < 5:
            away_names.append(name)
            away_ids.append(pid)

    return home_names, home_ids, away_names, away_ids


def _build_game_from_stats(summary: dict, actions: list[dict]) -> Game:
    """Build a Game from stats.nba.com playbyplayv3 actions + boxscoresummaryv2 summary."""
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
    home_lineup, home_lineup_ids, away_lineup, away_lineup_ids = _infer_starters_stats(
        period1_actions, pid_to_team, pid_to_name, home_abbr, away_abbr
    )

    events: list[PlayByPlayEvent] = []
    home_score_running = 0
    away_score_running = 0

    for action in actions:
        action_type = action.get("actionType", "")
        sub_type = action.get("subType", "")
        pid = int(action.get("personId") or 0)
        team = action.get("teamTricode") or ""
        desc = action.get("description") or ""

        if action_type == "Substitution":
            name_out = pid_to_name.get(pid)
            sub_result = _parse_sub_description(desc, team, pid_to_name, pid_to_team)
            if name_out and sub_result:
                name_in, pid_in = sub_result
                if team == home_abbr:
                    home_lineup_ids = [pid_in if home_lineup[i] == name_out else home_lineup_ids[i]
                                       for i in range(len(home_lineup))]
                    home_lineup = [name_in if n == name_out else n for n in home_lineup]
                elif team == away_abbr:
                    away_lineup_ids = [pid_in if away_lineup[i] == name_out else away_lineup_ids[i]
                                       for i in range(len(away_lineup))]
                    away_lineup = [name_in if n == name_out else n for n in away_lineup]

        # scoreHome/scoreAway are "" on non-scoring events; carry forward when absent
        raw_home = action.get("scoreHome") or ""
        raw_away = action.get("scoreAway") or ""
        if raw_home and raw_away:
            try:
                home_score_running = int(raw_home)
                away_score_running = int(raw_away)
            except ValueError:
                pass

        clock = _parse_iso_clock(action.get("clock") or "PT00M00.00S")
        events.append(PlayByPlayEvent(
            period=int(action["period"]),
            clock=clock,
            event_type=_v3_event_type(action_type, sub_type, desc),
            description=desc,
            home_score=home_score_running,
            away_score=away_score_running,
            home_players=tuple(home_lineup),
            away_players=tuple(away_lineup),
            home_player_ids=tuple(home_lineup_ids),
            away_player_ids=tuple(away_lineup_ids),
        ))

    final = events[-1] if events else None
    logger.debug(
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
        home_team_id=summary["home_team_id"],
        away_team_id=summary["visitor_team_id"],
        events=events,
    )


class GameNotPlayedError(Exception):
    pass


def scrape_game(game_id: str) -> Game:
    """Fetch play-by-play data for a single game and return a Game object.

    Uses stats.nba.com playbyplayv3, covering the 1996-97 season onward.
    Raises GameNotPlayedError if the game has no play-by-play data (postponed,
    cancelled, or pre-1996-97).
    """
    logger.debug("Scraping game %s", game_id)
    try:
        summary = fetch_stats_summary(game_id)
        actions = fetch_stats_pbp(game_id)
    except requests.HTTPError as e:
        raise GameNotPlayedError(f"Game {game_id} not available on stats.nba.com") from e
    if not actions:
        raise GameNotPlayedError(f"Game {game_id} has no play-by-play data")
    return _build_game_from_stats(summary, actions)
