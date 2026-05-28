"""Inspect a stored NBA game pickle in human-readable form.

Usage:
    python -m src.inspect_game <game_id>
    python -m src.inspect_game <game_id> --period 2
    python -m src.inspect_game <game_id> --type substitution
    python -m src.inspect_game <game_id> --lineups
    python -m src.inspect_game <game_id> --period 3 --lineups
"""
import argparse
import sys

from src.models.game import PlayByPlayEvent
from src.storage import game_exists, load_game


def _lineup_diff(team: str, before: tuple, after: tuple) -> str:
    added = next((p for p in after if p not in before), "?")
    removed = next((p for p in before if p not in after), "?")
    return (
        f"    {team}: {added} in / {removed} out\n"
        f"    lineup: {', '.join(after)}"
    )


def _print_event(
    ev: PlayByPlayEvent,
    prev: PlayByPlayEvent | None,
    show_lineups: bool,
    home_team: str,
    away_team: str,
) -> None:
    print(ev)
    if not show_lineups:
        return

    period_changed = prev is None or ev.period != prev.period
    if period_changed:
        print(f"    {home_team}: {', '.join(ev.home_players) or '(unknown)'}")
        print(f"    {away_team}: {', '.join(ev.away_players) or '(unknown)'}")
        return

    if ev.event_type == "substitution" and prev is not None:
        if ev.home_players != prev.home_players:
            print(_lineup_diff(home_team, prev.home_players, ev.home_players))
        if ev.away_players != prev.away_players:
            print(_lineup_diff(away_team, prev.away_players, ev.away_players))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a stored NBA game file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Event types: start_period, end_period, field_goal, missed_field_goal,\n"
            "             free_throw, rebound, turnover, foul, violation,\n"
            "             substitution, timeout, jump_ball"
        ),
    )
    parser.add_argument("game_id", help="NBA game ID, e.g. 0022400463")
    parser.add_argument("--period", type=int, metavar="N", help="Show only period N (1–4+)")
    parser.add_argument(
        "--type", dest="event_type", metavar="TYPE",
        help="Filter by event type, e.g. substitution or field_goal",
    )
    parser.add_argument(
        "--lineups", action="store_true",
        help="Print lineup at each period start and on every substitution",
    )
    args = parser.parse_args()

    if not game_exists(args.game_id):
        print(f"error: game '{args.game_id}' not found in storage.", file=sys.stderr)
        sys.exit(1)

    game = load_game(args.game_id)
    print(game)

    events = game.events
    if args.period is not None:
        events = [e for e in events if e.period == args.period]
    if args.event_type:
        events = [e for e in events if e.event_type == args.event_type]

    if not events:
        print("  (no events match the filter)")
        return

    filters = []
    if args.period:
        filters.append(f"period {args.period}")
    if args.event_type:
        filters.append(args.event_type)
    filter_note = f"  [{', '.join(filters)}]" if filters else ""
    print(f"  {len(events)} event(s){filter_note}\n")

    prev: PlayByPlayEvent | None = None
    for ev in events:
        _print_event(ev, prev, args.lineups, game.home_team_abbr, game.away_team_abbr)
        prev = ev


if __name__ == "__main__":
    main()
