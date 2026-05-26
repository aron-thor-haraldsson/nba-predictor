"""
Tests for player_scorer.

The scoring contract: a player whose on-court attack rate equals twice the
baseline should receive attack=2.0; a player who halves the opponent's
scoring rate should receive defence=0.5.
"""
import pytest

from src.scoring.player_scorer import score_player, score_all_players


def test_score_player_not_implemented():
    with pytest.raises(NotImplementedError):
        score_player(player_name="Myles Turner", team="Indiana Pacers", games=[], baseline={})


def test_score_all_players_not_implemented():
    with pytest.raises(NotImplementedError):
        score_all_players(games=[], baseline={})
