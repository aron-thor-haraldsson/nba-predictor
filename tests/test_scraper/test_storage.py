import datetime

from src.models.game import Game
from src.storage import save_game, load_game, game_exists, game_path


def _sample_game() -> Game:
    return Game(
        game_id="test_001",
        date=datetime.date(2020, 1, 1),
        home_team_abbr="IND",
        away_team_abbr="DET",
    )


def test_game_path_uses_game_id(tmp_path):
    path = game_path("abc123", games_dir=str(tmp_path))
    assert path.endswith("abc123.pkl")


def test_game_not_found_before_save(tmp_path):
    assert not game_exists("test_001", games_dir=str(tmp_path))


def test_save_creates_file(tmp_path):
    game = _sample_game()
    save_game(game, games_dir=str(tmp_path))
    assert game_exists(game.game_id, games_dir=str(tmp_path))


def test_save_and_load_roundtrip(tmp_path):
    game = _sample_game()
    save_game(game, games_dir=str(tmp_path))
    loaded = load_game(game.game_id, games_dir=str(tmp_path))
    assert loaded.game_id == game.game_id
    assert loaded.home_team_abbr == game.home_team_abbr
    assert loaded.date == game.date
