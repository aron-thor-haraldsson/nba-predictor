# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

NBA game outcome predictor. Scrapes play-by-play data, derives per-player productivity scores relative to a baseline player, and predicts game outcomes.

Python 3.10, virtualenv at `.venv/`.

## Commands

```bash
source .venv/bin/activate
pip install -r requirements.txt

pytest                                          # run all tests
pytest tests/test_models/test_game.py           # run a single file
pytest tests/test_models/test_game.py::test_game_defaults  # run one test
```

## Architecture

```
src/
  constants.py        — BASE_DIR, DATA_DIR, GAMES_DIR, JSON_CACHE_DIR, LOG_DIR, PLAYERS_CSV,
                        TEAMS_CSV, TEAMS_HISTORY_CSV, BASE_TEAM, BASE_PLAYER, BASE_SEASON, BASE_GAME_ID
  logging_config.py   — setup_logging(); call once from the entry point
  models/
    game.py           — PlayByPlayEvent, Game (dataclasses)
    player.py         — PlayerScore (attack/defence floats), Player
    team.py           — Team
  scraper/
    stats_scraper.py  — fetch_stats_summary(game_id), fetch_stats_pbp(game_id) [stats.nba.com]
    game_scraper.py   — scrape_game(game_id) -> Game
    season_scraper.py — scrape_season(year), scrape_all_seasons(start, end)
    storage.py        — save_game / load_game / game_exists  (pickle, keyed by game_id)
    lookup_scraper.py — fetch_players(), fetch_teams(), fetch_teams_history() → CSV lookup tables
  scoring/
    base_scorer.py    — compute_on_off_rates(), compute_baseline_rates()
    player_scorer.py  — score_player(), score_all_players()
    team_scorer.py    — aggregate_team_score()
  predictor/
    game_predictor.py — predict() [with court times], predict_from_lineups() [teams only]

data/
  raw/games/          — one .pkl per game (gitignored)
  raw/json/           — cached stats.nba.com responses ({game_id}_stats_summary.json, {game_id}_stats_pbp.json)
  raw/seasons/        — season-level index files
  raw/players.csv     — all historical players: person_id, player_name, player_name_i, full_name
  raw/teams.csv       — 30 active franchises: team_id, team_tricode, team_full_name (current name)
  raw/teams_history.csv — one row per franchise era: team_id, team_city, team_name, start_year, end_year
  processed/          — scored player/team data

tests/           — mirrors src/ layout; test_scraper/, test_models/, test_scoring/
```

## Development phases

1. **Scraping & storage** ✓ *complete*: `scrape_game()`, `scrape_season()`, `scrape_all_seasons()` implemented via `stats.nba.com` (playbyplayv3 + boxscoresummaryv2), covering 1996-97 onward.
2. **Base player scoring** ← *current focus*: on/off court per-minute rates for James Johnson (Indiana Pacers) define the 1.0 attack/defence baseline. Score all Pacers players relative to him, across one game → full season → all history.
3. **Expand to all teams**: repeat scoring for every team; use weighted averaging for cross-team ratios to limit error compounding.
4. **Global relative scores**: unify all player scores across teams relative to the 1.0 baseline. Consider tracking score drift over time.
5. **Prediction (known lineups)**: given players + expected court time → win probability and score margin.
6. **Prediction (teams only)**: estimate court times from historical averages when only starting lineups are known.

## Key design decisions

**Scoring model**: each player has `attack` and `defence` floats relative to the base player (James Johnson, Indiana Pacers = 1.0 / 1.0). Scores are derived from on-court vs off-court per-minute scoring rates across play-by-play data. `defence` is inverted: 0.5 means the opponent scores at half the rate, which is *better*.

**Cross-team comparison**: players who never share court time are linked via weighted averages of ratio chains to reduce compounding error (see `ChatGPT_chats/robust_productivity_ratio_estimation.txt`).

**Player and team IDs**: `Game` stores `home_team_id`/`away_team_id` (int); `PlayByPlayEvent` stores `home_player_ids`/`away_player_ids` as `tuple[int, ...]`, parallel to the name tuples. Use `players.csv` / `teams.csv` to resolve IDs to display names. Existing pickles without IDs will have `0` / empty tuples for these fields and should be re-scraped from the JSON cache.

**Player pairs**: represented as plain `tuple[str, str]`, not a custom class.

**Data source**: `stats.nba.com`, accessed via `requests` with a full Chrome browser header set. Covers 1996-97 onward. `storage.game_exists()` must always be checked before scraping to avoid redundant API calls.

**Path management**: all paths derive from `BASE_DIR = project root` in `constants.py` using `os.path`. Storage functions accept an optional `games_dir` parameter so tests can redirect to `tmp_path` without mocking.

**Logging**: configured once via `setup_logging()` in `logging_config.py`. Each module gets its own `logger = logging.getLogger(__name__)`.
