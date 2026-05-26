"""
Game outcome predictor.

Phase 1: predict() — teams and per-player court time are known.
Phase 2: predict_from_lineups() — only teams (and optional starters) are known;
         historical average court times are used to fill the gaps.
"""
import logging

from src.models.player import Player

logger = logging.getLogger(__name__)

# (Player, minutes_expected_on_court)
PlayerMinutes = tuple[Player, float]


def predict(
    home_players: list[PlayerMinutes],
    away_players: list[PlayerMinutes],
) -> dict[str, float]:
    """
    Predict game outcome given exact player lineups and expected court times.

    Returns {'home_win_probability': float, 'predicted_margin': float}.
    """
    raise NotImplementedError


def predict_from_lineups(
    home_team: str,
    away_team: str,
    starters: dict[str, list[str]] | None = None,
) -> dict[str, float]:
    """
    Predict from team names and optional starting lineups.
    Falls back to historical average minutes per player when starters are unknown.
    """
    raise NotImplementedError
