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

from src.constants import BASE_GAME_ID
from src.scraper.game_scraper import _build_game, scrape_game

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
