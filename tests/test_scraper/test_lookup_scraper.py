import csv
import io
from unittest.mock import MagicMock, call, patch

import pytest

from src.scraper.lookup_scraper import (
    _load_players,
    _load_teams_history,
    _load_teams,
    _save_players,
    _save_teams_history,
    _save_teams,
    fetch_players,
    fetch_teams_history,
    fetch_teams,
)


# --- fixtures ---

def _make_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = payload
    return mock


def _players_payload():
    return {
        "resultSets": [
            {
                "name": "CommonAllPlayers",
                "headers": [
                    "PERSON_ID", "DISPLAY_LAST_COMMA_FIRST", "DISPLAY_FIRST_LAST",
                    "ROSTERSTATUS", "FROM_YEAR", "TO_YEAR",
                ],
                "rowSet": [
                    [1629637, "Hayes, Jaxson", "Jaxson Hayes", 1, "2019", "2025"],
                    [2544, "James, LeBron", "LeBron James", 1, "2003", "2025"],
                    [76001, "Abdelnaby, Alaa", "Alaa Abdelnaby", 0, "1990", "1994"],
                    [203954, "Martin Jr., Kenyon", "Kenyon Martin Jr.", 1, "2015", "2025"],
                ],
            }
        ]
    }


def _franchise_payload():
    return {
        "resultSets": [
            {
                "name": "FranchiseHistory",
                "headers": ["LEAGUE_ID", "TEAM_ID", "TEAM_CITY", "TEAM_NAME", "START_YEAR", "END_YEAR"],
                "rowSet": [
                    ["00", 1610612737, "Atlanta", "Hawks", "1949", "2025"],
                    ["00", 1610612737, "St. Louis", "Hawks", "1955", "1967"],
                    ["00", 1610612760, "Oklahoma City", "Thunder", "2008", "2025"],
                    ["00", 1610612760, "Seattle", "SuperSonics", "1967", "2007"],
                ],
            },
            {
                "name": "DefunctTeams",
                "headers": ["LEAGUE_ID", "TEAM_ID", "TEAM_CITY", "TEAM_NAME", "START_YEAR", "END_YEAR"],
                "rowSet": [],
            },
        ]
    }


def _team_years_payload():
    return {
        "resultSets": [
            {
                "name": "TeamYears",
                "headers": ["LEAGUE_ID", "TEAM_ID", "MIN_YEAR", "MAX_YEAR", "ABBREVIATION"],
                "rowSet": [
                    ["00", 1610612737, "1949", "2025", "ATL"],
                    ["00", 1610612760, "1967", "2025", "OKC"],
                    ["00", 9999999999, "1946", "1949", None],  # defunct, no tricode
                ],
            }
        ]
    }


# --- fetch_players ---

def test_fetch_players_returns_expected_fields(tmp_path):
    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", str(tmp_path / "players.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_players_payload())):
        players = fetch_players()
    assert all(
        {"person_id", "player_name", "player_name_i", "full_name"} <= set(p)
        for p in players
    )


def test_fetch_players_simple_name(tmp_path):
    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", str(tmp_path / "players.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_players_payload())):
        players = fetch_players()
    hayes = next(p for p in players if p["person_id"] == 1629637)
    assert hayes["player_name"] == "Hayes"
    assert hayes["player_name_i"] == "J. Hayes"
    assert hayes["full_name"] == "Jaxson Hayes"


def test_fetch_players_suffix_in_last_name(tmp_path):
    """'Martin Jr., Kenyon' → player_name='Martin Jr.', player_name_i='K. Martin Jr.'"""
    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", str(tmp_path / "players.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_players_payload())):
        players = fetch_players()
    martin = next(p for p in players if p["full_name"] == "Kenyon Martin Jr.")
    assert martin["player_name"] == "Martin Jr."
    assert martin["player_name_i"] == "K. Martin Jr."


def test_fetch_players_person_id_is_int(tmp_path):
    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", str(tmp_path / "players.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_players_payload())):
        players = fetch_players()
    assert all(isinstance(p["person_id"], int) for p in players)


def test_fetch_players_uses_cache(tmp_path):
    players_data = [{"person_id": 99, "player_name": "Cached", "player_name_i": "C. Cached", "full_name": "Cached Player"}]
    with open(tmp_path / "players.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["person_id", "player_name", "player_name_i", "full_name"])
        writer.writeheader()
        writer.writerows(players_data)

    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", str(tmp_path / "players.csv")), \
         patch("src.scraper.lookup_scraper.requests.get") as mock_get:
        result = fetch_players()
        mock_get.assert_not_called()
    assert result[0]["full_name"] == "Cached Player"


def test_fetch_players_saves_csv(tmp_path):
    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", str(tmp_path / "players.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_players_payload())):
        fetch_players()
    assert (tmp_path / "players.csv").exists()


# --- fetch_teams ---

def test_fetch_teams_returns_expected_fields(tmp_path):
    with patch("src.scraper.lookup_scraper.TEAMS_CSV", str(tmp_path / "teams.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               side_effect=[
                   _make_response(_franchise_payload()),
                   _make_response(_team_years_payload()),
               ]):
        teams = fetch_teams()
    assert all({"team_id", "team_tricode", "team_full_name"} <= set(t) for t in teams)


def test_fetch_teams_uses_most_recent_name(tmp_path):
    """OKC franchise was Seattle SuperSonics before 2008; current name should win."""
    with patch("src.scraper.lookup_scraper.TEAMS_CSV", str(tmp_path / "teams.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               side_effect=[
                   _make_response(_franchise_payload()),
                   _make_response(_team_years_payload()),
               ]):
        teams = fetch_teams()
    okc = next(t for t in teams if t["team_id"] == 1610612760)
    assert okc["team_full_name"] == "Oklahoma City Thunder"
    assert okc["team_tricode"] == "OKC"


def test_fetch_teams_excludes_defunct_no_tricode(tmp_path):
    """Teams with no tricode in commonteamyears are excluded."""
    with patch("src.scraper.lookup_scraper.TEAMS_CSV", str(tmp_path / "teams.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               side_effect=[
                   _make_response(_franchise_payload()),
                   _make_response(_team_years_payload()),
               ]):
        teams = fetch_teams()
    ids = {t["team_id"] for t in teams}
    assert 9999999999 not in ids


def test_fetch_teams_team_id_is_int(tmp_path):
    with patch("src.scraper.lookup_scraper.TEAMS_CSV", str(tmp_path / "teams.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               side_effect=[
                   _make_response(_franchise_payload()),
                   _make_response(_team_years_payload()),
               ]):
        teams = fetch_teams()
    assert all(isinstance(t["team_id"], int) for t in teams)


def test_fetch_teams_uses_cache(tmp_path):
    teams_data = [{"team_id": 42, "team_tricode": "TST", "team_full_name": "Test Team"}]
    with open(tmp_path / "teams.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["team_id", "team_tricode", "team_full_name"])
        writer.writeheader()
        writer.writerows(teams_data)

    with patch("src.scraper.lookup_scraper.TEAMS_CSV", str(tmp_path / "teams.csv")), \
         patch("src.scraper.lookup_scraper.requests.get") as mock_get:
        result = fetch_teams()
        mock_get.assert_not_called()
    assert result[0]["team_full_name"] == "Test Team"


def test_fetch_teams_saves_csv(tmp_path):
    with patch("src.scraper.lookup_scraper.TEAMS_CSV", str(tmp_path / "teams.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               side_effect=[
                   _make_response(_franchise_payload()),
                   _make_response(_team_years_payload()),
               ]):
        fetch_teams()
    assert (tmp_path / "teams.csv").exists()


# --- round-trip CSV serialisation ---

def test_players_csv_roundtrip(tmp_path):
    original = [
        {"person_id": 1, "player_name": "Hayes", "player_name_i": "J. Hayes", "full_name": "Jaxson Hayes"},
        {"person_id": 2, "player_name": "James", "player_name_i": "L. James", "full_name": "LeBron James"},
    ]
    csv_path = str(tmp_path / "players.csv")
    with patch("src.scraper.lookup_scraper.PLAYERS_CSV", csv_path):
        _save_players(original)
        loaded = _load_players()
    assert loaded == original


def test_teams_csv_roundtrip(tmp_path):
    original = [
        {"team_id": 1610612737, "team_tricode": "ATL", "team_full_name": "Atlanta Hawks"},
    ]
    csv_path = str(tmp_path / "teams.csv")
    with patch("src.scraper.lookup_scraper.TEAMS_CSV", csv_path):
        _save_teams(original)
        loaded = _load_teams()
    assert loaded == original


# --- fetch_teams_history ---

def test_fetch_teams_history_returns_expected_fields(tmp_path):
    with patch("src.scraper.lookup_scraper.TEAMS_HISTORY_CSV", str(tmp_path / "teams_history.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_franchise_payload())):
        history = fetch_teams_history()
    assert all(
        {"team_id", "team_city", "team_name", "start_year", "end_year"} <= set(r)
        for r in history
    )


def test_fetch_teams_history_returns_all_eras(tmp_path):
    """Every franchise era row is returned, not just the most recent."""
    with patch("src.scraper.lookup_scraper.TEAMS_HISTORY_CSV", str(tmp_path / "teams_history.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_franchise_payload())):
        history = fetch_teams_history()
    okc_eras = [r for r in history if r["team_id"] == 1610612760]
    names = {r["team_name"] for r in okc_eras}
    assert names == {"Thunder", "SuperSonics"}


def test_fetch_teams_history_numeric_types(tmp_path):
    with patch("src.scraper.lookup_scraper.TEAMS_HISTORY_CSV", str(tmp_path / "teams_history.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_franchise_payload())):
        history = fetch_teams_history()
    assert all(isinstance(r["team_id"], int) for r in history)
    assert all(isinstance(r["start_year"], int) for r in history)
    assert all(isinstance(r["end_year"], int) for r in history)


def test_fetch_teams_history_uses_cache(tmp_path):
    cached = [{"team_id": 42, "team_city": "Cached", "team_name": "Team", "start_year": 2000, "end_year": 2010}]
    with open(tmp_path / "teams_history.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["team_id", "team_city", "team_name", "start_year", "end_year"])
        writer.writeheader()
        writer.writerows(cached)

    with patch("src.scraper.lookup_scraper.TEAMS_HISTORY_CSV", str(tmp_path / "teams_history.csv")), \
         patch("src.scraper.lookup_scraper.requests.get") as mock_get:
        result = fetch_teams_history()
        mock_get.assert_not_called()
    assert result[0]["team_city"] == "Cached"


def test_fetch_teams_history_saves_csv(tmp_path):
    with patch("src.scraper.lookup_scraper.TEAMS_HISTORY_CSV", str(tmp_path / "teams_history.csv")), \
         patch("src.scraper.lookup_scraper.requests.get",
               return_value=_make_response(_franchise_payload())):
        fetch_teams_history()
    assert (tmp_path / "teams_history.csv").exists()


def test_teams_history_csv_roundtrip(tmp_path):
    original = [
        {"team_id": 1610612760, "team_city": "Oklahoma City", "team_name": "Thunder", "start_year": 2008, "end_year": 2025},
        {"team_id": 1610612760, "team_city": "Seattle", "team_name": "SuperSonics", "start_year": 1967, "end_year": 2007},
    ]
    csv_path = str(tmp_path / "teams_history.csv")
    with patch("src.scraper.lookup_scraper.TEAMS_HISTORY_CSV", csv_path):
        _save_teams_history(original)
        loaded = _load_teams_history()
    assert loaded == original
