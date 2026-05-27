"""
Tests for game_scraper using the Indiana Pacers' first 2025 game as a fixture.

Base game: IND @ MIA  2025-01-02  (game_id 0022400463)
  Final: MIA 115 – IND 128  (IND is the away team)
  425 play-by-play events across 4 periods
"""
import datetime
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import requests

from src.constants import BASE_GAME_ID
from src.scraper.game_scraper import (
    _build_game,
    _build_game_from_stats,
    _parse_iso_clock,
    _v3_event_type,
    scrape_game,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ind_mia_detail() -> dict:
    with open(FIXTURES / f"{BASE_GAME_ID}_gamedetail.json") as f:
        return json.load(f)["g"]


@pytest.fixture
def ind_mia_pbp() -> list[list[dict]]:
    periods = []
    for p in range(1, 5):
        with open(FIXTURES / f"{BASE_GAME_ID}_pbp_{p}.json") as f:
            periods.append(json.load(f)["g"]["pla"])
    return periods


# --- _build_game: metadata ---

def test_build_game_id(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    assert game.game_id == BASE_GAME_ID


def test_build_game_date(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    assert game.date == datetime.date(2025, 1, 2)


def test_build_game_teams(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    assert game.home_team_abbr == "MIA"
    assert game.away_team_abbr == "IND"


# --- _build_game: scoring ---

def test_build_game_final_score(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    final = game.events[-1]
    assert final.home_score == 115
    assert final.away_score == 128


def test_build_game_event_count(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    assert len(game.events) == 425


# --- _build_game: lineups ---

def test_build_game_away_starters_include_haliburton(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    first = next(e for e in game.events if e.event_type != "start_period")
    assert "Tyrese Haliburton" in first.away_players


def test_build_game_home_starters_include_adebayo(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    first = next(e for e in game.events if e.event_type != "start_period")
    assert "Bam Adebayo" in first.home_players


def test_build_game_lineup_has_five_players(ind_mia_detail, ind_mia_pbp):
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    first = next(e for e in game.events if e.event_type != "start_period")
    assert len(first.home_players) == 5
    assert len(first.away_players) == 5


def test_build_game_lineup_updates_on_sub(ind_mia_detail, ind_mia_pbp):
    # First sub in this game: MIA Adebayo out → Rozier in
    game = _build_game(ind_mia_detail, ind_mia_pbp)
    sub_idx = next(i for i, e in enumerate(game.events) if e.event_type == "substitution")
    before = game.events[sub_idx - 1]
    after = game.events[sub_idx]
    assert "Bam Adebayo" in before.home_players
    assert "Bam Adebayo" not in after.home_players
    assert "Terry Rozier" in after.home_players


# --- scrape_game: CDN wiring ---

def test_scrape_game_calls_cdn_functions(ind_mia_detail, ind_mia_pbp):
    with (
        patch("src.scraper.game_scraper.fetch_gamedetail", return_value=ind_mia_detail) as mock_detail,
        patch("src.scraper.game_scraper.fetch_pbp", side_effect=[{"pla": p} for p in ind_mia_pbp]) as mock_pbp,
    ):
        game = scrape_game(BASE_GAME_ID)

    mock_detail.assert_called_once_with(BASE_GAME_ID)
    assert mock_pbp.call_count == 4
    assert game.game_id == BASE_GAME_ID


# --- _parse_iso_clock and _v3_event_type unit tests ---

def test_parse_iso_clock_full_minute():
    assert _parse_iso_clock("PT12M00.00S") == "12:00.0"

def test_parse_iso_clock_partial():
    assert _parse_iso_clock("PT05M30.50S") == "5:30.5"

def test_parse_iso_clock_seconds_only():
    assert _parse_iso_clock("PT00M45.00S") == "0:45.0"

def test_v3_event_type_field_goal():
    assert _v3_event_type("2pt", "", "Haliburton 2-pt Shot") == "field_goal"

def test_v3_event_type_missed_field_goal():
    assert _v3_event_type("3pt", "", "MISS Haliburton 3-pt Shot") == "missed_field_goal"

def test_v3_event_type_period_end():
    assert _v3_event_type("period", "end", "") == "end_period"

def test_v3_event_type_period_start():
    assert _v3_event_type("period", "start", "") == "start_period"

def test_v3_event_type_substitution():
    assert _v3_event_type("substitution", "out", "") == "substitution"


# --- _build_game_from_stats fixtures (playbyplayv3 action format) ---

def _v3_action(action_number, action_type, sub_type, period, clock,
               team_id=0, team_tricode="", person_id=0, player_name="",
               description="", score_home=0, score_away=0, is_field_goal=0):
    return {
        "actionNumber": action_number,
        "clock": clock,
        "period": period,
        "teamId": team_id,
        "teamTricode": team_tricode,
        "personId": person_id,
        "playerName": player_name,
        "actionType": action_type,
        "subType": sub_type,
        "description": description,
        "scoreHome": str(score_home),
        "scoreAway": str(score_away),
        "isFieldGoal": is_field_goal,
        "videoAvailable": 0,
    }


@pytest.fixture
def stats_summary():
    return {
        "game_id": "0022500001",
        "game_date_est": "2025-10-22",
        "home_team_id": 1111,
        "home_team_abbr": "HOM",
        "visitor_team_id": 2222,
        "visitor_team_abbr": "VIS",
    }


@pytest.fixture
def stats_actions():
    """Minimal game: period 1 with a shot and a sub, periods 2-4 empty."""
    return [
        # period 1 start
        _v3_action(1, "period", "start", 1, "PT12M00.00S"),
        # home player 1 (Alice) scores 2 pts
        _v3_action(2, "2pt", "", 1, "PT11M30.00S",
                   team_id=1111, team_tricode="HOM", person_id=1, player_name="Alice A",
                   description="Alice A 2-pt Shot (2 PTS)", score_home=2, score_away=0,
                   is_field_goal=1),
        # visitor player 11 (Vera) scores 2 pts
        _v3_action(3, "2pt", "", 1, "PT11M00.00S",
                   team_id=2222, team_tricode="VIS", person_id=11, player_name="Vera V",
                   description="Vera V 2-pt Shot (2 PTS)", score_home=2, score_away=2,
                   is_field_goal=1),
        # home substitution: Eve E (5) out, Frank F (6) in — two separate actions
        _v3_action(4, "substitution", "out", 1, "PT10M00.00S",
                   team_id=1111, team_tricode="HOM", person_id=5, player_name="Eve E",
                   description="Eve E Substitution", score_home=2, score_away=2),
        _v3_action(5, "substitution", "in", 1, "PT10M00.00S",
                   team_id=1111, team_tricode="HOM", person_id=6, player_name="Frank F",
                   description="Frank F Substitution", score_home=2, score_away=2),
        # period 1 end
        _v3_action(6, "period", "end", 1, "PT00M00.00S",
                   score_home=2, score_away=2),
        # periods 2-4 (start + end only)
        _v3_action(7, "period", "start", 2, "PT12M00.00S"),
        _v3_action(8, "period", "end", 2, "PT00M00.00S", score_home=2, score_away=2),
        _v3_action(9, "period", "start", 3, "PT12M00.00S"),
        _v3_action(10, "period", "end", 3, "PT00M00.00S", score_home=2, score_away=2),
        _v3_action(11, "period", "start", 4, "PT12M00.00S"),
        _v3_action(12, "period", "end", 4, "PT00M00.00S", score_home=2, score_away=2),
    ]


def _make_starter_actions(team_id, team_tricode, starter_ids, bench_ids, prefix):
    """Period-1 actions establishing starters before any sub."""
    actions = []
    for i, pid in enumerate(starter_ids + bench_ids):
        name = f"{prefix}{pid}"
        actions.append(_v3_action(
            100 + i, "rebound", "", 1, "PT12M00.00S",
            team_id=team_id, team_tricode=team_tricode,
            person_id=pid, player_name=name,
            description=f"{name} Rebound",
        ))
    return actions


@pytest.fixture
def stats_actions_with_full_lineups(stats_actions):
    """Prepend period-1 events for all 10 players so starters can be inferred."""
    home = _make_starter_actions(1111, "HOM", [1, 2, 3, 4, 5], [6], "H")
    away = _make_starter_actions(2222, "VIS", [11, 12, 13, 14, 15], [16], "V")
    return home + away + stats_actions


# --- _build_game_from_stats: metadata ---

def test_build_game_from_stats_game_id(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    assert game.game_id == "0022500001"


def test_build_game_from_stats_date(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    assert game.date == datetime.date(2025, 10, 22)


def test_build_game_from_stats_teams(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    assert game.home_team_abbr == "HOM"
    assert game.away_team_abbr == "VIS"


# --- _build_game_from_stats: scoring ---

def test_build_game_from_stats_score_tracking(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    final = game.events[-1]
    assert final.home_score == 2
    assert final.away_score == 2


def test_build_game_from_stats_score_zero_before_first_basket(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    # First event (period start) should have 0-0
    assert game.events[0].home_score == 0
    assert game.events[0].away_score == 0


def test_build_game_from_stats_event_count(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    assert len(game.events) == len(stats_actions_with_full_lineups)


# --- _build_game_from_stats: clock normalisation ---

def test_build_game_from_stats_clock_gets_decimal(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    for event in game.events:
        assert "." in event.clock, f"Missing decimal in clock: {event.clock!r}"


# --- _build_game_from_stats: substitutions ---

def test_build_game_from_stats_sub_updates_lineup(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    # v3 subs are two events: "out" then "in" — the lineup updates at the "in" event
    sub_indices = [i for i, e in enumerate(game.events) if e.event_type == "substitution"]
    sub_out_idx, sub_in_idx = sub_indices[0], sub_indices[1]
    before = game.events[sub_out_idx - 1]   # event before the "out"
    after = game.events[sub_in_idx]          # "in" event — lineup is updated here
    assert "Eve E" in before.home_players
    assert "Eve E" not in after.home_players
    assert "Frank F" in after.home_players


def test_build_game_from_stats_sub_does_not_change_away_lineup(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    sub_idx = next(i for i, e in enumerate(game.events) if e.event_type == "substitution")
    before = game.events[sub_idx - 1]
    after = game.events[sub_idx]
    assert before.away_players == after.away_players


# --- scrape_game: stats.nba.com fallback ---

def test_scrape_game_falls_back_when_cdn_has_no_periods(stats_summary, stats_actions_with_full_lineups):
    """CDN returns p=0 (placeholder/unarchived) → falls back to stats.nba.com."""
    with (
        patch("src.scraper.game_scraper.fetch_gamedetail", return_value={"p": 0}),
        patch("src.scraper.game_scraper.fetch_stats_summary", return_value=stats_summary) as mock_sum,
        patch("src.scraper.game_scraper.fetch_stats_pbp", return_value=stats_actions_with_full_lineups) as mock_pbp,
    ):
        game = scrape_game("0022500001")

    mock_sum.assert_called_once_with("0022500001")
    mock_pbp.assert_called_once_with("0022500001")
    assert game.game_id == "0022500001"


def test_scrape_game_falls_back_when_cdn_pbp_is_empty(ind_mia_detail, stats_summary, stats_actions_with_full_lineups):
    """CDN has period data but all PBP lists are empty → falls back to stats.nba.com."""
    empty_pbp = [{"pla": []}] * 4
    with (
        patch("src.scraper.game_scraper.fetch_gamedetail", return_value=ind_mia_detail),
        patch("src.scraper.game_scraper.fetch_pbp", side_effect=empty_pbp),
        patch("src.scraper.game_scraper.fetch_stats_summary", return_value=stats_summary),
        patch("src.scraper.game_scraper.fetch_stats_pbp", return_value=stats_actions_with_full_lineups),
    ):
        game = scrape_game("0022500001")
    assert game.game_id == "0022500001"


def test_scrape_game_raises_when_both_sources_unavailable():
    from src.scraper.game_scraper import GameNotPlayedError
    with (
        patch("src.scraper.game_scraper.fetch_gamedetail", return_value={"p": 0}),
        patch("src.scraper.game_scraper.fetch_stats_summary",
              side_effect=requests.HTTPError("404")),
    ):
        with pytest.raises(GameNotPlayedError):
            scrape_game("0022500001")
