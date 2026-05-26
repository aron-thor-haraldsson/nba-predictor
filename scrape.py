from src.logging_config import setup_logging
from src.scraper.game_scraper import scrape_game
from src.scraper.season_scraper import _completed_game_ids, _load_schedule
from src.scraper.storage import game_exists, load_game, save_game

setup_logging()

SEASON_YEAR = 2020
NUM_GAMES = 250 # Use 'None' for all

# --- Step 1: fetch and cache the schedule ---
print(f"Loading {SEASON_YEAR} season schedule...")
schedule = _load_schedule(SEASON_YEAR)
all_ids = _completed_game_ids(schedule)
print(f"  {len(all_ids)} completed games found.\n")

# --- Step 2: scrape, parse and pickle the first N games ---
print(f"Scraping first {NUM_GAMES} games of the {SEASON_YEAR} season...\n")
for game_id in all_ids[:NUM_GAMES]:
    if game_exists(game_id):
        game = load_game(game_id)
        status = "cached"
    else:
        game = scrape_game(game_id)
        save_game(game)
        status = "scraped"
    print(f"  [{status}] {game}")
