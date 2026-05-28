"""Inspect the local game cache.

Usage:
    python -m src.inspect_cache
    python -m src.inspect_cache --season 2025
    python -m src.inspect_cache --season 2025 --list
"""
import argparse
from collections import Counter

from src.storage import _cached_game_ids, _season_end_year


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the local game cache.")
    parser.add_argument("--season", type=int, metavar="YEAR",
                        help="Filter to a single season by end year (e.g. 2025 for 2024-25)")
    parser.add_argument("--list", action="store_true", dest="list_ids",
                        help="Print individual game IDs instead of a summary")
    args = parser.parse_args()

    all_ids = _cached_game_ids()

    if args.season:
        ids = [gid for gid in all_ids if _season_end_year(gid) == args.season]
    else:
        ids = all_ids

    if args.list_ids:
        for gid in ids:
            print(gid)
    elif args.season:
        print(f"{args.season - 1}-{str(args.season)[-2:]} season: {len(ids)} game(s)")
    else:
        counts = Counter(_season_end_year(gid) for gid in ids)
        print(f"{'Season':<10} {'Games':>6}")
        print("-" * 18)
        for year in sorted(counts):
            label = f"{year - 1}-{str(year)[-2:]}"
            print(f"{label:<10} {counts[year]:>6}")
        print("-" * 18)
        print(f"{'Total':<10} {len(ids):>6}")


if __name__ == "__main__":
    main()
