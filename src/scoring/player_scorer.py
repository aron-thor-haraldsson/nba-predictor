"""
Scores each player's attack and defence relative to the base player (1.0).

attack  = player's on-court attack rate / base player's on-court attack rate
defence = base player's on-court defence rate / player's on-court defence rate
          (inverted so that a lower opponent scoring rate gives a higher score)

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
