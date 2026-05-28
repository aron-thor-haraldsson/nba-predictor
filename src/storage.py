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
