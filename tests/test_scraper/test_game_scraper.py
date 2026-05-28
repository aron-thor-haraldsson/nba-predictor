"""
Tests for game_scraper (stats.nba.com / playbyplayv3 path).
"""
import datetime
import json
from unittest.mock import patch

import pytest
import requests

from src.scraper.game_scraper import (
    GameNotPlayedError,
    _build_game_from_stats,
    _parse_iso_clock,
    _parse_sub_description,
    _v3_event_type,
    scrape_game,
)


# --- _parse_iso_clock ---

def test_parse_iso_clock_full_minute():
    assert _parse_iso_clock("PT12M00.00S") == "12:00.0"

def test_parse_iso_clock_partial():
    assert _parse_iso_clock("PT05M30.50S") == "5:30.5"

def test_parse_iso_clock_seconds_only():
    assert _parse_iso_clock("PT00M45.00S") == "0:45.0"


# --- _v3_event_type ---

def test_v3_event_type_field_goal():
    assert _v3_event_type("Made Shot", "Jump Shot", "") == "field_goal"

def test_v3_event_type_missed_field_goal():
    assert _v3_event_type("Missed Shot", "Pullup Jump shot", "") == "missed_field_goal"

def test_v3_event_type_free_throw():
    assert _v3_event_type("Free Throw", "Free Throw 1 of 2", "") == "free_throw"

def test_v3_event_type_period_end():
    assert _v3_event_type("period", "end", "") == "end_period"

def test_v3_event_type_period_start():
    assert _v3_event_type("period", "start", "") == "start_period"

def test_v3_event_type_substitution():
    assert _v3_event_type("Substitution", "", "SUB: Rozier FOR Adebayo") == "substitution"

def test_v3_event_type_unknown_passes_through():
    assert _v3_event_type("Instant Replay", "Coach Challenge Overturn Ruling", "") == "instant_replay"


# --- _parse_sub_description ---

def test_parse_sub_description_finds_incoming_player():
    pid_to_name = {1: "Alice A", 6: "Frank F"}
    pid_to_team = {1: "HOM", 6: "HOM"}
    result = _parse_sub_description("SUB: Frank FOR Alice", "HOM", pid_to_name, pid_to_team)
    assert result == ("Frank F", 6)

def test_parse_sub_description_returns_none_when_no_match():
    pid_to_name = {1: "Alice A"}
    pid_to_team = {1: "HOM"}
    result = _parse_sub_description("SUB: Nobody FOR Alice", "HOM", pid_to_name, pid_to_team)
    assert result is None

def test_parse_sub_description_returns_none_for_malformed():
    result = _parse_sub_description("Not a sub description", "HOM", {}, {})
    assert result is None


# --- _build_game_from_stats fixtures (playbyplayv3 action format) ---
#
# Real v3 format notes:
#   - actionType is Title Case: "Made Shot", "Substitution", "Rebound", etc.
#   - Substitutions are a single event: personId = player OUT, description = "SUB: X FOR Y"
#   - scoreHome/scoreAway are "" on non-scoring events; the running score is carried forward
#   - Period events use lowercase "period" with subType "start"/"end"

def _v3_action(action_number, action_type, sub_type, period, clock,
               team_id=0, team_tricode="", person_id=0, player_name="",
               description="", score_home="", score_away="", is_field_goal=0):
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
        "scoreHome": score_home,
        "scoreAway": score_away,
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
    """Minimal game: period 1 with two shots and one substitution, periods 2-4 empty."""
    return [
        # period 1 start — period events carry the score as "0"/"0" at tip-off
        _v3_action(1, "period", "start", 1, "PT12M00.00S", score_home="0", score_away="0"),
        # home player Alice A (1) scores 2 pts
        _v3_action(2, "Made Shot", "Driving Layup Shot", 1, "PT11M30.00S",
                   team_id=1111, team_tricode="HOM", person_id=1, player_name="Alice A",
                   description="Alice A 2' Driving Layup (2 PTS)", score_home="2", score_away="0",
                   is_field_goal=1),
        # visitor Vera V (11) scores 2 pts
        _v3_action(3, "Made Shot", "Jump Shot", 1, "PT11M00.00S",
                   team_id=2222, team_tricode="VIS", person_id=11, player_name="Vera V",
                   description="Vera V 14' Jump Shot (2 PTS)", score_home="2", score_away="2",
                   is_field_goal=1),
        # home substitution: Eve E (5) out, Frank F (6) in — single event
        _v3_action(4, "Substitution", "", 1, "PT10M00.00S",
                   team_id=1111, team_tricode="HOM", person_id=5, player_name="Eve E",
                   description="SUB: Frank FOR Eve"),
        # period 1 end — non-scoring; score carries forward from last basket
        _v3_action(5, "period", "end", 1, "PT00M00.00S"),
        # periods 2-4 (start + end only)
        _v3_action(6, "period", "start", 2, "PT12M00.00S"),
        _v3_action(7, "period", "end", 2, "PT00M00.00S"),
        _v3_action(8, "period", "start", 3, "PT12M00.00S"),
        _v3_action(9, "period", "end", 3, "PT00M00.00S"),
        _v3_action(10, "period", "start", 4, "PT12M00.00S"),
        _v3_action(11, "period", "end", 4, "PT00M00.00S"),
    ]


def _make_starter_actions(team_id, team_tricode, starters, bench):
    """Period-1 rebound actions establishing rosters before any sub.

    starters and bench are lists of (pid, name) tuples.
    Using real names ensures _parse_sub_description can match the name fragment
    from description "SUB: X FOR Y" against pid_to_name.
    """
    actions = []
    for i, (pid, name) in enumerate(starters + bench):
        actions.append(_v3_action(
            100 + i, "Rebound", "Unknown", 1, "PT12M00.00S",
            team_id=team_id, team_tricode=team_tricode,
            person_id=pid, player_name=name,
            description=f"{name} Rebound",
        ))
    return actions


@pytest.fixture
def stats_actions_with_full_lineups(stats_actions):
    """Prepend period-1 events for all 10 players so starters and bench are in pid_to_name."""
    home = _make_starter_actions(1111, "HOM",
        starters=[(1, "Alice A"), (2, "Bob B"), (3, "Carol C"), (4, "Dave D"), (5, "Eve E")],
        bench=[(6, "Frank F")],
    )
    away = _make_starter_actions(2222, "VIS",
        starters=[(11, "Vera V"), (12, "Wanda W"), (13, "Xena X"), (14, "Yara Y"), (15, "Zoe Z")],
        bench=[(16, "Victor V")],
    )
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
    assert game.home_team_id == 1111
    assert game.away_team_id == 2222


# --- _build_game_from_stats: scoring ---

def test_build_game_from_stats_score_tracking(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    final = game.events[-1]
    assert final.home_score == 2
    assert final.away_score == 2

def test_build_game_from_stats_score_zero_before_first_basket(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    first_score_idx = next(i for i, e in enumerate(game.events) if e.home_score > 0 or e.away_score > 0)
    for e in game.events[:first_score_idx]:
        assert e.home_score == 0 and e.away_score == 0

def test_build_game_from_stats_score_carries_forward(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    sub_event = next(e for e in game.events if e.event_type == "substitution")
    assert sub_event.home_score == 2
    assert sub_event.away_score == 2

def test_build_game_from_stats_event_count(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    assert len(game.events) == len(stats_actions_with_full_lineups)


# --- _build_game_from_stats: clock ---

def test_build_game_from_stats_clock_gets_decimal(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    for event in game.events:
        assert "." in event.clock, f"Missing decimal in clock: {event.clock!r}"


# --- _build_game_from_stats: substitutions ---

def test_build_game_from_stats_sub_updates_lineup(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    sub_idx = next(i for i, e in enumerate(game.events) if e.event_type == "substitution")
    before = game.events[sub_idx - 1]
    after = game.events[sub_idx]
    assert "Eve E" in before.home_players
    assert "Eve E" not in after.home_players
    assert "Frank F" in after.home_players

def test_build_game_from_stats_sub_does_not_change_away_lineup(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    sub_idx = next(i for i, e in enumerate(game.events) if e.event_type == "substitution")
    before = game.events[sub_idx - 1]
    after = game.events[sub_idx]
    assert before.away_players == after.away_players


def test_build_game_from_stats_sub_updates_lineup_ids(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    sub_idx = next(i for i, e in enumerate(game.events) if e.event_type == "substitution")
    before = game.events[sub_idx - 1]
    after = game.events[sub_idx]
    assert 5 in before.home_player_ids   # Eve E (pid 5) on court before sub
    assert 5 not in after.home_player_ids
    assert 6 in after.home_player_ids    # Frank F (pid 6) on court after sub


def test_build_game_from_stats_player_ids_parallel_to_names(stats_summary, stats_actions_with_full_lineups):
    game = _build_game_from_stats(stats_summary, stats_actions_with_full_lineups)
    for event in game.events:
        assert len(event.home_player_ids) == len(event.home_players)
        assert len(event.away_player_ids) == len(event.away_players)


# --- scrape_game ---

def test_scrape_game_calls_stats_functions(stats_summary, stats_actions_with_full_lineups):
    with (
        patch("src.scraper.game_scraper.fetch_stats_summary", return_value=stats_summary) as mock_sum,
        patch("src.scraper.game_scraper.fetch_stats_pbp", return_value=stats_actions_with_full_lineups) as mock_pbp,
    ):
        game = scrape_game("0022500001")
    mock_sum.assert_called_once_with("0022500001")
    mock_pbp.assert_called_once_with("0022500001")
    assert game.game_id == "0022500001"

def test_scrape_game_raises_on_http_error():
    with patch("src.scraper.game_scraper.fetch_stats_summary",
               side_effect=requests.HTTPError("404")):
        with pytest.raises(GameNotPlayedError):
            scrape_game("0022500001")

def test_scrape_game_raises_when_actions_empty(stats_summary):
    with (
        patch("src.scraper.game_scraper.fetch_stats_summary", return_value=stats_summary),
        patch("src.scraper.game_scraper.fetch_stats_pbp", return_value=[]),
    ):
        with pytest.raises(GameNotPlayedError):
            scrape_game("0022500001")
