import json
from unittest.mock import MagicMock, patch

import pytest

from src.scraper.stats_scraper import (
    NBA_STATS_BASE,
    _find_result_set,
    _rowset_to_dicts,
    fetch_stats_pbp,
    fetch_stats_summary,
)


# --- helpers ---

def _make_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = payload
    return mock


def _summary_payload(game_id="0022500001"):
    return {
        "resultSets": [
            {
                "name": "GameSummary",
                "headers": [
                    "GAME_DATE_EST", "GAME_SEQUENCE", "GAME_ID", "GAME_STATUS_ID",
                    "GAME_STATUS_TEXT", "GAMECODE", "HOME_TEAM_ID", "VISITOR_TEAM_ID",
                ],
                "rowSet": [
                    ["2025-10-22T00:00:00", 1, game_id, 3, "Final", "20251022/VISHOM",
                     1111, 2222],
                ],
            },
            {
                "name": "LineScore",
                "headers": ["GAME_DATE_EST", "GAME_SEQUENCE", "GAME_ID", "TEAM_ID", "TEAM_ABBREVIATION"],
                "rowSet": [
                    ["2025-10-22T00:00:00", 1, game_id, 1111, "HOM"],
                    ["2025-10-22T00:00:00", 2, game_id, 2222, "VIS"],
                ],
            },
        ]
    }


def _pbp_payload(game_id="0022500001"):
    return {
        "game": {
            "gameId": game_id,
            "actions": [
                {
                    "actionNumber": 1,
                    "clock": "PT12M00.00S",
                    "period": 1,
                    "teamId": 0,
                    "teamTricode": "",
                    "personId": 0,
                    "playerName": "",
                    "actionType": "period",
                    "subType": "start",
                    "description": "Start of Period",
                    "scoreHome": "0",
                    "scoreAway": "0",
                    "isFieldGoal": 0,
                    "videoAvailable": 0,
                }
            ],
        }
    }


# --- _rowset_to_dicts ---

def test_rowset_to_dicts_basic():
    rs = {"headers": ["A", "B"], "rowSet": [[1, 2], [3, 4]]}
    result = _rowset_to_dicts(rs)
    assert result == [{"A": 1, "B": 2}, {"A": 3, "B": 4}]


def test_rowset_to_dicts_empty():
    rs = {"headers": ["A", "B"], "rowSet": []}
    assert _rowset_to_dicts(rs) == []


# --- _find_result_set ---

def test_find_result_set_found():
    result_sets = [{"name": "PlayByPlay", "headers": [], "rowSet": []}]
    assert _find_result_set(result_sets, "PlayByPlay") == result_sets[0]


def test_find_result_set_not_found():
    with pytest.raises(ValueError, match="GameSummary"):
        _find_result_set([], "GameSummary")


# --- fetch_stats_summary ---

def test_fetch_stats_summary_constructs_url(tmp_path):
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(_summary_payload())) as mock_get:
        fetch_stats_summary("0022500001")
        url = mock_get.call_args[0][0]
    assert "boxscoresummaryv2" in url
    assert NBA_STATS_BASE in url


def test_fetch_stats_summary_sends_nba_headers(tmp_path):
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(_summary_payload())) as mock_get:
        fetch_stats_summary("0022500001")
        headers = mock_get.call_args[1]["headers"]
    assert "Referer" in headers
    assert "x-nba-stats-origin" in headers


def test_fetch_stats_summary_parses_metadata(tmp_path):
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(_summary_payload())):
        result = fetch_stats_summary("0022500001")
    assert result["game_date_est"] == "2025-10-22"
    assert result["home_team_abbr"] == "HOM"
    assert result["visitor_team_abbr"] == "VIS"
    assert result["home_team_id"] == 1111
    assert result["visitor_team_id"] == 2222


def test_fetch_stats_summary_strips_time_from_date(tmp_path):
    """GAME_DATE_EST sometimes includes a time component."""
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(_summary_payload())):
        result = fetch_stats_summary("0022500001")
    assert result["game_date_est"] == "2025-10-22"
    assert "T" not in result["game_date_est"]


def test_fetch_stats_summary_uses_cache(tmp_path):
    cached = {"game_id": "0022500001", "game_date_est": "2025-10-22",
              "home_team_id": 1111, "home_team_abbr": "HOM",
              "visitor_team_id": 2222, "visitor_team_abbr": "VIS"}
    cache_file = tmp_path / "0022500001_stats_summary.json"
    cache_file.write_text(json.dumps(cached))

    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get") as mock_get:
        result = fetch_stats_summary("0022500001")
        mock_get.assert_not_called()
    assert result == cached


# --- fetch_stats_pbp ---

def test_fetch_stats_pbp_constructs_url(tmp_path):
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(_pbp_payload())) as mock_get:
        fetch_stats_pbp("0022500001")
        url = mock_get.call_args[0][0]
    assert "playbyplayv3" in url
    assert NBA_STATS_BASE in url


def test_fetch_stats_pbp_returns_list_of_dicts(tmp_path):
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(_pbp_payload())):
        actions = fetch_stats_pbp("0022500001")
    assert isinstance(actions, list)
    assert isinstance(actions[0], dict)
    assert "actionType" in actions[0]
    assert "clock" in actions[0]
    assert "scoreHome" in actions[0]


def test_fetch_stats_pbp_does_not_cache_empty_response(tmp_path):
    empty_payload = {"game": {"gameId": "0022500001", "actions": []}}
    with patch("src.scraper.stats_scraper.JSON_CACHE_DIR", str(tmp_path)), \
         patch("src.scraper.stats_scraper.requests.get",
               return_value=_make_response(empty_payload)):
        fetch_stats_pbp("0022500001")
    assert not (tmp_path / "0022500001_stats_pbp.json").exists()
