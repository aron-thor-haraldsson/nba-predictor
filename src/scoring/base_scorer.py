"""
Derives the baseline productivity rates from the base player (James Johnson,
Indiana Pacers) whose attack and defence are defined as 1.0.

For a given game, the play-by-play is segmented into intervals where the base
player is on court vs off court. Per-minute scoring rates for and against the
team are computed for each segment. The on-court rates become the 1.0 baseline.
"""
import logging

from src.models.game import Game

logger = logging.getLogger(__name__)

# on_attack:   points scored by base player's team per minute while he is on court
# on_defence:  points scored by opponent per minute while he is on court
# off_attack:  points scored by base player's team per minute while he is off court
# off_defence: points scored by opponent per minute while he is off court
OnOffRates = dict[str, float]


def compute_on_off_rates(game: Game, player_name: str, team: str) -> OnOffRates:
    """
    Compute per-minute scoring rates for a player's team while that player is
    on-court vs off-court for a single game.
    """
    raise NotImplementedError


def compute_baseline_rates(games: list[Game], player_name: str, team: str) -> OnOffRates:
    """Average on/off rates across multiple games to establish a stable baseline."""
    raise NotImplementedError
