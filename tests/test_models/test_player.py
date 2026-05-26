from src.models.player import Player, PlayerScore


def test_player_score_defaults():
    score = PlayerScore()
    assert score.attack == 1.0
    assert score.defence == 1.0


def test_player_defaults_to_base_score():
    player = Player(name="James Johnson", team="Indiana Pacers")
    assert player.score.attack == 1.0
    assert player.score.defence == 1.0


def test_player_custom_score():
    player = Player(
        name="Some Player",
        team="Indiana Pacers",
        score=PlayerScore(attack=2.0, defence=0.5),
    )
    assert player.score.attack == 2.0
    assert player.score.defence == 0.5


def test_player_score_str():
    s = str(PlayerScore(attack=1.5, defence=0.75))
    assert "attack=1.50" in s
    assert "defence=0.75" in s


def test_player_str_contains_name_and_team():
    player = Player(name="James Johnson", team="Indiana Pacers")
    s = str(player)
    assert "James Johnson" in s
    assert "Indiana Pacers" in s


def test_player_str_contains_scores():
    player = Player(
        name="James Johnson",
        team="Indiana Pacers",
        score=PlayerScore(attack=2.0, defence=0.5),
    )
    s = str(player)
    assert "attack=2.00" in s
    assert "defence=0.50" in s
