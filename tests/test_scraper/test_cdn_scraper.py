import json
from unittest.mock import MagicMock, patch

from src.constants import BASE_GAME_ID, BASE_SEASON
from src.scraper.cdn_scraper import _season_year, fetch_gamedetail, fetch_pbp


def test_season_year_base_game():
    assert _season_year(BASE_GAME_ID) == BASE_SEASON


def test_season_year_2019_20():
    assert _season_year("0021900001") == 2019


def test_season_year_2000_01():
    assert _season_year("0020000001") == 2000


def _mock_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = payload
    return mock


def test_fetch_pbp_constructs_url():
    payload = {"g": {"pla": []}}
    with patch("src.scraper.cdn_scraper.requests.get", return_value=_mock_response(payload)) as mock_get:
        fetch_pbp(BASE_GAME_ID, 2)
        url = mock_get.call_args[0][0]
    assert str(BASE_SEASON) in url
    assert BASE_GAME_ID in url
    assert "_2_pbp.json" in url


def test_fetch_gamedetail_constructs_url():
    payload = {"g": {}}
    with patch("src.scraper.cdn_scraper.requests.get", return_value=_mock_response(payload)) as mock_get:
        fetch_gamedetail(BASE_GAME_ID)
        url = mock_get.call_args[0][0]
    assert str(BASE_SEASON) in url
    assert BASE_GAME_ID in url
    assert "gamedetail" in url
