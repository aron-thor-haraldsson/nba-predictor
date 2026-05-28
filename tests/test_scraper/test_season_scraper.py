import datetime
from unittest.mock import patch

import pytest

from src.models.game import Game, PlayByPlayEvent
from src.scraper.game_scraper import GameNotPlayedError
from src.scraper.season_scraper import _json_cached, _print_game_line, scrape_season


def _make_event(home_score=110, away_score=105):
    return PlayByPlayEvent(
        period=4, clock="0:00.0", event_type="end_period", description="",
        home_score=home_score, away_score=away_score,
        home_players=(), away_players=(),
    )


def _make_game(game_id="0022500001", home_score=110, away_score=105, n_events=200):
    return Game(
        game_id=game_id,
        date=datetime.date(2025, 1, 15),
        home_team_abbr="HOM",
        away_team_abbr="VIS",
        home_team_id=1111,
        away_team_id=2222,
        events=[_make_event(home_score, away_score)] * n_events,
    )


# --- _json_cached ---

def test_json_cached_true_when_both_files_exist(tmp_path):
    (tmp_path / "0022500001_stats_summary.json").write_text("{}")
    (tmp_path / "0022500001_stats_pbp.json").write_text("[]")
    with patch("src.scraper.season_scraper.JSON_CACHE_DIR", str(tmp_path)):
        assert _json_cached("0022500001") is True


def test_json_cached_false_when_only_summary_exists(tmp_path):
    (tmp_path / "0022500001_stats_summary.json").write_text("{}")
    with patch("src.scraper.season_scraper.JSON_CACHE_DIR", str(tmp_path)):
        assert _json_cached("0022500001") is False


def test_json_cached_false_when_only_pbp_exists(tmp_path):
    (tmp_path / "0022500001_stats_pbp.json").write_text("[]")
    with patch("src.scraper.season_scraper.JSON_CACHE_DIR", str(tmp_path)):
        assert _json_cached("0022500001") is False


def test_json_cached_false_when_neither_exists(tmp_path):
    with patch("src.scraper.season_scraper.JSON_CACHE_DIR", str(tmp_path)):
        assert _json_cached("0022500001") is False


# --- _print_game_line ---

def test_print_game_line_contains_expected_fields(capsys):
    _print_game_line("[pkl cached]", _make_game(home_score=110, away_score=105, n_events=200))
    out = capsys.readouterr().out
    assert "[pkl cached]" in out
    assert "0022500001" in out
    assert "HOM vs VIS" in out
    assert "110-105" in out
    assert "200 events" in out


def test_print_game_line_short_prefix_is_padded(capsys):
    _print_game_line("[scraped]", _make_game())
    out = capsys.readouterr().out
    assert out.startswith("[scraped]     [")


def test_print_game_line_full_prefix_not_padded(capsys):
    _print_game_line("[half-scrape]", _make_game())
    out = capsys.readouterr().out
    assert out.startswith("[half-scrape] [")


def test_print_game_line_no_events(capsys):
    game = Game(
        game_id="0022500001", date=datetime.date(2025, 1, 15),
        home_team_abbr="HOM", away_team_abbr="VIS",
        home_team_id=1111, away_team_id=2222, events=[],
    )
    _print_game_line("[scraped]", game)
    out = capsys.readouterr().out
    assert "0-0" in out
    assert "0 events" in out


# --- scrape_season ---

def test_scrape_season_loads_from_pkl(capsys):
    game = _make_game()
    with (
        patch("src.scraper.season_scraper._load_game_ids", return_value=["0022500001"]),
        patch("src.scraper.season_scraper.game_exists", return_value=True),
        patch("src.scraper.season_scraper.load_game", return_value=game) as mock_load,
        patch("src.scraper.season_scraper.scrape_game") as mock_scrape,
    ):
        result = scrape_season(2025)
    mock_load.assert_called_once_with("0022500001")
    mock_scrape.assert_not_called()
    assert result == [game]
    assert "[pkl cached]" in capsys.readouterr().out


def test_scrape_season_half_scrape_prefix_when_json_cached(capsys):
    game = _make_game()
    with (
        patch("src.scraper.season_scraper._load_game_ids", return_value=["0022500001"]),
        patch("src.scraper.season_scraper.game_exists", return_value=False),
        patch("src.scraper.season_scraper._json_cached", return_value=True),
        patch("src.scraper.season_scraper.scrape_game", return_value=game),
        patch("src.scraper.season_scraper.save_game"),
    ):
        scrape_season(2025)
    assert "[half-scrape]" in capsys.readouterr().out


def test_scrape_season_scraped_prefix_when_no_cache(capsys):
    game = _make_game()
    with (
        patch("src.scraper.season_scraper._load_game_ids", return_value=["0022500001"]),
        patch("src.scraper.season_scraper.game_exists", return_value=False),
        patch("src.scraper.season_scraper._json_cached", return_value=False),
        patch("src.scraper.season_scraper.scrape_game", return_value=game),
        patch("src.scraper.season_scraper.save_game"),
    ):
        scrape_season(2025)
    assert "[scraped]" in capsys.readouterr().out


def test_scrape_season_saves_newly_scraped_game():
    game = _make_game()
    with (
        patch("src.scraper.season_scraper._load_game_ids", return_value=["0022500001"]),
        patch("src.scraper.season_scraper.game_exists", return_value=False),
        patch("src.scraper.season_scraper._json_cached", return_value=False),
        patch("src.scraper.season_scraper.scrape_game", return_value=game),
        patch("src.scraper.season_scraper.save_game") as mock_save,
    ):
        scrape_season(2025)
    mock_save.assert_called_once_with(game)


def test_scrape_season_skips_game_not_played():
    with (
        patch("src.scraper.season_scraper._load_game_ids", return_value=["0022500001"]),
        patch("src.scraper.season_scraper.game_exists", return_value=False),
        patch("src.scraper.season_scraper._json_cached", return_value=False),
        patch("src.scraper.season_scraper.scrape_game",
              side_effect=GameNotPlayedError("no data")),
        patch("src.scraper.season_scraper.save_game") as mock_save,
    ):
        result = scrape_season(2025)
    assert result == []
    mock_save.assert_not_called()


def test_scrape_season_returns_all_games():
    games = [_make_game(f"002250000{i}") for i in range(3)]
    with (
        patch("src.scraper.season_scraper._load_game_ids",
              return_value=[g.game_id for g in games]),
        patch("src.scraper.season_scraper.game_exists", return_value=False),
        patch("src.scraper.season_scraper._json_cached", return_value=False),
        patch("src.scraper.season_scraper.scrape_game", side_effect=list(games)),
        patch("src.scraper.season_scraper.save_game"),
    ):
        result = scrape_season(2025)
    assert result == games
