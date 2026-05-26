import datetime

from src.models.game import Game, PlayByPlayEvent


def test_game_defaults():
    game = Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr="IND",
        away_team_abbr="DET",
    )
    assert game.game_id == "0021900001"
    assert game.events == []


def test_play_by_play_event_fields():
    event = PlayByPlayEvent(
        period=1,
        clock="10:30",
        event_type="field_goal",
        description="James Johnson makes 2-pt shot",
        home_score=2,
        away_score=0,
        home_players=("James Johnson", "Myles Turner"),
        away_players=("Blake Griffin", "Andre Drummond"),
    )
    assert event.period == 1
    assert event.home_score == 2
    assert "James Johnson" in event.home_players


def test_game_accepts_events():
    event = PlayByPlayEvent(
        period=1, clock="12:00", event_type="tip_off", description="Tip off",
        home_score=0, away_score=0,
        home_players=(), away_players=(),
    )
    game = Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr="IND",
        away_team_abbr="DET",
        events=[event],
    )
    assert len(game.events) == 1


def test_event_str_contains_key_fields():
    event = PlayByPlayEvent(
        period=2, clock="5:42", event_type="field_goal",
        description="James Johnson makes 2-pt shot",
        home_score=54, away_score=48,
        home_players=("James Johnson",), away_players=(),
    )
    s = str(event)
    assert "Q2" in s
    assert "5:42" in s
    assert "field_goal" in s
    assert "54-48" in s


def test_game_str_no_events():
    game = Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr="IND",
        away_team_abbr="DET",
    )
    s = str(game)
    assert "IND" in s
    assert "DET" in s
    assert "no score" in s


def test_game_str_with_events():
    event = PlayByPlayEvent(
        period=4, clock="0:00", event_type="end_game", description="End of game",
        home_score=110, away_score=98,
        home_players=(), away_players=(),
    )
    game = Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr="IND",
        away_team_abbr="DET",
        events=[event],
    )
    s = str(game)
    assert "110-98" in s
    assert "1 events" in s


def test_game_describe_truncates():
    events = [
        PlayByPlayEvent(
            period=1, clock="12:00", event_type="tip_off", description=f"Event {i}",
            home_score=i, away_score=0, home_players=(), away_players=(),
        )
        for i in range(25)
    ]
    game = Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr="IND",
        away_team_abbr="DET",
        events=events,
    )
    description = game.describe(max_events=5)
    assert "20 more events" in description


def test_game_describe_no_events():
    game = Game(
        game_id="0021900001",
        date=datetime.date(2019, 10, 22),
        home_team_abbr="IND",
        away_team_abbr="DET",
    )
    assert "no events" in game.describe()
