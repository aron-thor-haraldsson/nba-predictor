# CLAUDE.md

## Project

NBA game outcome predictor. Scrapes play-by-play data, derives per-player productivity scores relative to a baseline player, and predicts game outcomes.

Python 3.10, virtualenv at `.venv/`. Install: `pip install -e ".[dev]"`.

## Commands

```bash
source .venv/bin/activate

pytest                                          # run all tests
pytest tests/test_models/test_game.py           # run a single file
pytest tests/test_models/test_game.py::test_game_defaults  # run one test
```

## CLI tools

```bash
# Scraping
python -m src.scraper.game_scraper <game_id>              # scrape a single game
python -m src.scraper.game_scraper <game_id> --force      # re-scrape even if cached
python -m src.scraper.season_scraper --season 2025        # scrape one season (end year)
python -m src.scraper.season_scraper --season 2025 --force  # re-fetch game ID list too
python -m src.scraper.season_scraper --all                # scrape all seasons from 1996-97

# Lookup tables (always force-refreshes from the API)
python -m src.scraper.lookup_scraper --fetch-players
python -m src.scraper.lookup_scraper --fetch-teams
python -m src.scraper.lookup_scraper --fetch-teams-history
python -m src.scraper.lookup_scraper --fetch-all-lookup

# Inspection
python -m src.inspect_cache                               # summary of cached games by season
python -m src.inspect_cache --season 2025                 # count for one season
python -m src.inspect_cache --season 2025 --list          # print individual game IDs
python -m src.inspect_game <game_id>                      # print all events for a game
python -m src.inspect_game <game_id> --period 2           # filter by period
python -m src.inspect_game <game_id> --type substitution  # filter by event type
python -m src.inspect_game <game_id> --lineups            # show lineup at each change
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
  storage.py          — save_game / load_game / game_exists  (pickle, keyed by game_id)
  scraper/
    api_client.py     — fetch_stats_summary(game_id), fetch_stats_pbp(game_id) [stats.nba.com HTTP]
    game_scraper.py   — scrape_game(game_id) -> Game
    season_scraper.py — scrape_season(year), scrape_all_seasons(start, end)
    lookup_scraper.py — fetch_players(), fetch_teams(), fetch_teams_history() → CSV lookup tables
  scoring/
    baseline_scorer.py — compute_on_off_rates(), compute_baseline_rates()
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

## Key design decisions

**Scoring model**: each player has `attack` and `defence` floats relative to the base player (James Johnson, Indiana Pacers = 1.0 / 1.0). Scores are derived from on-court vs off-court per-minute scoring rates across play-by-play data. `defence` is inverted: 0.5 means the opponent scores at half the rate, which is *better*.

**Cross-team comparison**: players who never share court time are linked via weighted averages of ratio chains to reduce compounding error.

**Player and team IDs**: `Game` stores `home_team_id`/`away_team_id` (int); `PlayByPlayEvent` stores `home_player_ids`/`away_player_ids` as `tuple[int, ...]`, parallel to the name tuples. Use `players.csv` / `teams.csv` to resolve IDs to display names.

**Player pairs**: represented as plain `tuple[str, str]`, not a custom class.

**Data source**: `stats.nba.com`, accessed via `requests` with a full Chrome browser header set. Covers 1996-97 onward. `storage.game_exists()` must always be checked before scraping to avoid redundant API calls. The raw HTTP layer lives in `scraper/api_client.py`; scrapers call into it.

**Path management**: all paths derive from `BASE_DIR = project root` in `constants.py` using `os.path`. Storage functions accept an optional `games_dir` parameter so tests can redirect to `tmp_path` without mocking.

**Logging**: configured once via `setup_logging()` in `logging_config.py`. Each module gets its own `logger = logging.getLogger(__name__)`.
