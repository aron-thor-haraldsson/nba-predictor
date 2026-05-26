from src.models.player import Player, PlayerScore
from src.models.team import Team


def test_team_str_no_players():
    team = Team(name="Indiana Pacers")
    assert "Indiana Pacers" in str(team)
    assert "no players" in str(team)


def test_team_str_lists_players():
    team = Team(
        name="Indiana Pacers",
        players=[
            Player("James Johnson", "Indiana Pacers", PlayerScore(attack=1.0, defence=1.0)),
            Player("Myles Turner", "Indiana Pacers", PlayerScore(attack=1.2, defence=0.8)),
        ],
    )
    s = str(team)
    assert "Indiana Pacers" in s
    assert "James Johnson" in s
    assert "Myles Turner" in s
    assert "attack=1.20" in s
