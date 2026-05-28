"""
Scores each player's attack and defence relative to the base player (1.0).

attack  = player's on-court attack rate / base player's on-court attack rate
defence = player's on-court defence rate / base player's on-court defence rate
          (lower is better — 0.5 means opponent scores at half the baseline rate)

Cross-team ratios are combined using weighted averaging to reduce error
compounding when players are never directly compared (see
ChatGPT_chats/robust_productivity_ratio_estimation.txt).
"""
import logging

from src.models.game import Game
from src.models.player import Player, PlayerScore

logger = logging.getLogger(__name__)


def score_player(player_name: str, team: str, games: list[Game], baseline: dict) -> PlayerScore:
    """Compute attack/defence scores for one player relative to the baseline."""
    raise NotImplementedError


def score_all_players(games: list[Game], baseline: dict) -> list[Player]:
    """Score every player who appears in the given games."""
    raise NotImplementedError
