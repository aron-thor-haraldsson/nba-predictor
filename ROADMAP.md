# NBA Predictor — Development Roadmap

Phases are a guide, not a rigid contract — order and scope can be adjusted.

---

## Phase 1 — Data scraping & storage `[ COMPLETE ]`
- [x] Architecture scaffolded: models, scraper, scoring, predictor packages
- [x] `Game` and `PlayByPlayEvent` datatypes defined
- [x] Pickle storage (`save_game` / `load_game` / `game_exists`) implemented and tested
- [x] `scrape_game(game_id)` — fetches play-by-play from `stats.nba.com`
- [x] `scrape_season(year)` — scrapes all completed games of one season
- [x] `scrape_all_seasons(start, end)` — scrapes full historical record

> `stats.nba.com` responses are expensive to re-fetch; always check `game_exists()` before scraping. Season schedules are cached as JSON under `data/raw/seasons/`.

---

## Phase 2 — Score base player & base team `[ IN PROGRESS ]`
- Base team: **Indiana Pacers**. Base player: **James Johnson** (attack = 1.0, defence = 1.0).
- For each game, segment play time into on-court / off-court intervals per player.
- Compute per-minute scoring rates for-and-against during each segment.
- The base player's on-court rates define the 1.0 baseline.
- Score all other Pacers players as a multiplier vs the base player.
- Expand scope: one game → full season → all historical Pacers games.

---

## Phase 3 — Expand to all teams `[ NOT STARTED ]`
- Repeat Phase 2 for one other team, then all teams.
- Cross-team comparison uses weighted averaging over ratio chains to limit error
  compounding when players are never directly observed together.

---

## Phase 4 — Relative scores across all players `[ NOT STARTED ]`
- Unify all player scores so they are relative to each other and to the 1.0 baseline.
- Decide whether to track score drift over time (injury, improvement, ageing).

---

## Phase 5 — Prediction: known lineups `[ NOT STARTED ]`
- Given two teams, their players, and expected court time → win probability + score margin.

---

## Phase 6 — Prediction: teams & starters only `[ NOT STARTED ]`
- Estimate court times from historical averages when only starting lineups are known.
