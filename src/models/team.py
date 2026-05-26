from dataclasses import dataclass, field

from src.models.player import Player


@dataclass
class Team:
    name: str
    players: list[Player] = field(default_factory=list)

    def __str__(self) -> str:
        if not self.players:
            return f"{self.name} (no players)"
        lines = [self.name]
        for player in self.players:
            lines.append(f"  {player}")
        return "\n".join(lines)
