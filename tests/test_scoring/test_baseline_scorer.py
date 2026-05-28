"""
Tests for baseline_scorer.compute_on_off_rates.

These will be filled in once the scorer is implemented, but the structure
and expected contract is defined here to guide development.
"""
import pytest

from src.scoring.baseline_scorer import compute_on_off_rates, compute_baseline_rates


def test_compute_on_off_rates_not_implemented():
    # Placeholder: replace with a real Game fixture once game_scraper is built.
    with pytest.raises(NotImplementedError):
        compute_on_off_rates(game=None, player_name="James Johnson", team="Indiana Pacers")


def test_compute_baseline_rates_not_implemented():
    with pytest.raises(NotImplementedError):
        compute_baseline_rates(games=[], player_name="James Johnson", team="Indiana Pacers")
