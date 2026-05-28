"""
Pickle-based persistence for Game objects.

Each game is stored as <GAMES_DIR>/<game_id>.pkl.
Pass a custom games_dir to override the default (useful in tests).
"""
import argparse
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect the local game cache.")
    parser.add_argument("--season", type=int, metavar="YEAR",
                        help="Filter to a single season by end year (e.g. 2025 for 2024-25)")
    parser.add_argument("--list", action="store_true", dest="list_ids",
                        help="Print individual game IDs instead of a summary")
    args = parser.parse_args()

    all_ids = _cached_game_ids()

    if args.season:
        ids = [gid for gid in all_ids if _season_end_year(gid) == args.season]
    else:
        ids = all_ids

    if args.list_ids:
        for gid in ids:
            print(gid)
    elif args.season:
        print(f"{args.season - 1}-{str(args.season)[-2:]} season: {len(ids)} game(s)")
    else:
        from collections import Counter
        counts = Counter(_season_end_year(gid) for gid in ids)
        print(f"{'Season':<10} {'Games':>6}")
        print("-" * 18)
        for year in sorted(counts):
            label = f"{year - 1}-{str(year)[-2:]}"
            print(f"{label:<10} {counts[year]:>6}")
        print("-" * 18)
        print(f"{'Total':<10} {len(ids):>6}")
