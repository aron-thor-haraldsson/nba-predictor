import logging

from src.models.player import Player

logger = logging.getLogger(__name__)


def aggregate_team_score(players: list[Player]) -> dict[str, float]:
    """
    Return a weighted-average attack and defence score for a team based on
    its players' scores and historical average court times.
    """
    raise NotImplementedError
