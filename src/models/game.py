import datetime
from dataclasses import dataclass, field


@dataclass
class PlayByPlayEvent:
    """A single event from an NBA play-by-play record."""
    period: int
    clock: str                       # Time remaining in period, e.g. "10:30"
    event_type: str                  # e.g. "field_goal", "substitution", "foul"
    description: str
    home_score: int
    away_score: int
    home_players: tuple[str, ...]    # Names of home players on court at this moment
    away_players: tuple[str, ...]    # Names of away players on court at this moment

    def __str__(self) -> str:
        desc = self.description if len(self.description) <= 60 else self.description[:59] + "…"
        return (
            f"Q{self.period} {self.clock:>7} | {self.event_type:<18} | "
            f"{desc:<60} | {self.home_score}-{self.away_score}"
        )


@dataclass
class Game:
    """A complete NBA game with play-by-play data."""
    game_id: str
    date: datetime.date
    home_team_abbr: str
    away_team_abbr: str
    events: list[PlayByPlayEvent] = field(default_factory=list)

    def __str__(self) -> str:
        score = f"{self.events[-1].home_score}-{self.events[-1].away_score}" if self.events else "no score"
        return (
            f"[{self.game_id}] {self.date} | "
            f"{self.home_team_abbr} vs {self.away_team_abbr} | "
            f"{score} | {len(self.events)} events"
        )

    def describe(self, max_events: int = 10) -> str:
        """Return a multi-line summary with a sample of play-by-play events."""
        header = str(self)
        if not self.events:
            return header + "\n  (no events)"
        lines = [header]
        shown = self.events[:max_events]
        for event in shown:
            lines.append(f"  {event}")
        if len(self.events) > max_events:
            lines.append(f"  ... ({len(self.events) - max_events} more events)")
        return "\n".join(lines)
