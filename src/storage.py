"""
Pickle-based persistence for Game objects.

Each game is stored as <GAMES_DIR>/<game_id>.pkl.
Pass a custom games_dir to override the default (useful in tests).
"""
import logging
import os
import pickle

from src.constants import GAMES_DIR
from src.models.game import Game

logger = logging.getLogger(__name__)


def game_path(game_id: str, games_dir: str = GAMES_DIR) -> str:
    return os.path.join(games_dir, f"{game_id}.pkl")


def game_exists(game_id: str, games_dir: str = GAMES_DIR) -> bool:
    return os.path.isfile(game_path(game_id, games_dir))


def save_game(game: Game, games_dir: str = GAMES_DIR) -> None:
    path = game_path(game.game_id, games_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(game, f)
    logger.debug("Saved game %s to %s", game.game_id, path)


def load_game(game_id: str, games_dir: str = GAMES_DIR) -> Game:
    path = game_path(game_id, games_dir)
    with open(path, "rb") as f:
        return pickle.load(f)


def _cached_game_ids(games_dir: str = GAMES_DIR) -> list[str]:
    if not os.path.isdir(games_dir):
        return []
    return sorted(
        f[:-4] for f in os.listdir(games_dir) if f.endswith(".pkl")
    )


def _season_end_year(game_id: str) -> int:
    """Return the end year of the season encoded in a game ID (e.g. '0022400463' → 2025)."""
    two_digit = int(game_id[3:5])
    start_year = 1900 + two_digit if two_digit >= 96 else 2000 + two_digit
    return start_year + 1

