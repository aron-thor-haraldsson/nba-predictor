from dataclasses import dataclass, field


@dataclass
class PlayerScore:
    """
    Productivity scores relative to the base player (James Johnson = 1.0).

    attack:   multiplier on the team's per-minute scoring rate while on court.
    defence:  multiplier on the opponent's per-minute scoring rate while on court
              (lower is better — 0.5 means opponent scores at half the usual rate).
    """
    attack: float = 1.0
    defence: float = 1.0

    def __str__(self) -> str:
        return f"attack={self.attack:.2f}, defence={self.defence:.2f}"


@dataclass
class Player:
    name: str
    team: str
    score: PlayerScore = field(default_factory=PlayerScore)

    def __str__(self) -> str:
        return f"{self.name:<30} ({self.team}) | {self.score}"
