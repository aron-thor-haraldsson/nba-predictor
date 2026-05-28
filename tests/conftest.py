import datetime

import pytest

from src.models.game import Game, PlayByPlayEvent

# Shared team identifiers used across fixtures
HOME_ABBR = "IND"
AWAY_ABBR = "DET"
HOME_TEAM_ID = 1610612754
AWAY_TEAM_ID = 1610612765

_HOME_STARTERS = ("James Johnson", "Myles Turner", "Victor Oladipo", "Domantas Sabonis", "T.J. Warren")
_HOME_STARTER_IDS = (101, 102, 103, 104, 105)

# Lineup after T.J. Warren is subbed out for Doug McDermott in period 1
_HOME_LINEUP_2 = ("James Johnson", "Myles Turner", "Victor Oladipo", "Domantas Sabonis", "Doug McDermott")
_HOME_LINEUP_2_IDS = (101, 102, 103, 104, 106)

_AWAY_STARTERS = ("Blake Griffin", "Andre Drummond", "Reggie Jackson", "Luke Kennard", "Tony Snell")
_AWAY_STARTER_IDS = (201, 202, 203, 204, 205)


@pytest.fixture
def minimal_game() -> Game:
    """Game with no events — use for storage and metadata tests."""
    return Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr=HOME_ABBR,
        away_team_abbr=AWAY_ABBR,
        home_team_id=HOME_TEAM_ID,
        away_team_id=AWAY_TEAM_ID,
    )


@pytest.fixture
def sample_game() -> Game:
    """IND vs DET with two periods, scoring events, and one home substitution.

    Period 1: starters open, James Johnson scores (2-0), Blake Griffin scores (2-2),
              T.J. Warren subs out for Doug McDermott, Myles Turner scores (4-2).
    Period 2: starters return, no scoring, game ends 4-2.

    Use this for scoring and prediction tests that need real lineup intervals.
    """
    def _event(period, clock, event_type, description, home_score, away_score,
                home_players, home_player_ids, away_players, away_player_ids):
        return PlayByPlayEvent(
            period=period, clock=clock, event_type=event_type,
            description=description, home_score=home_score, away_score=away_score,
            home_players=home_players, home_player_ids=home_player_ids,
            away_players=away_players, away_player_ids=away_player_ids,
        )

    s, si = _HOME_STARTERS, _HOME_STARTER_IDS
    s2, si2 = _HOME_LINEUP_2, _HOME_LINEUP_2_IDS
    a, ai = _AWAY_STARTERS, _AWAY_STARTER_IDS

    events = [
        _event(1, "12:00.0", "start_period",  "Start of period 1",                        0, 0, s,  si,  a, ai),
        _event(1, "11:30.0", "field_goal",     "James Johnson 2' Driving Layup (2 PTS)",   2, 0, s,  si,  a, ai),
        _event(1, "11:00.0", "field_goal",     "Blake Griffin 14' Jump Shot (2 PTS)",       2, 2, s,  si,  a, ai),
        _event(1, "10:00.0", "substitution",   "SUB: Doug McDermott FOR T.J. Warren",       2, 2, s2, si2, a, ai),
        _event(1,  "9:00.0", "field_goal",     "Myles Turner Dunk (4 PTS)",                4, 2, s2, si2, a, ai),
        _event(1,  "0:00.0", "end_period",     "End of period 1",                          4, 2, s2, si2, a, ai),
        _event(2, "12:00.0", "start_period",   "Start of period 2",                        4, 2, s,  si,  a, ai),
        _event(2,  "0:00.0", "end_period",     "End of period 2",                          4, 2, s,  si,  a, ai),
    ]

    return Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr=HOME_ABBR,
        away_team_abbr=AWAY_ABBR,
        home_team_id=HOME_TEAM_ID,
        away_team_id=AWAY_TEAM_ID,
        events=events,
    )
