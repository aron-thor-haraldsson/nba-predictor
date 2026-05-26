import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
GAMES_DIR = os.path.join(RAW_DATA_DIR, "games")
SEASONS_DIR = os.path.join(RAW_DATA_DIR, "seasons")
JSON_CACHE_DIR = os.path.join(RAW_DATA_DIR, "json")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")

BASE_TEAM = "Indiana Pacers"
BASE_PLAYER = "James Johnson"
BASE_SEASON = 2024                  # start year of the 2024-25 season
BASE_GAME_ID = "0022400463"         # Indiana Pacers' first game of 2025 (IND @ MIA, 2025-01-02)

NBA_CDN_BASE = "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba"
NBA_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:72.0) "
        "Gecko/20100101 Firefox/72.0"
    ),
}
