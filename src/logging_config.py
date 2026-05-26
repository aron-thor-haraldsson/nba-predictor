import logging
import os
from logging.handlers import RotatingFileHandler

from src.constants import LOG_DIR


def setup_logging(level: int = logging.INFO) -> None:
    if logging.getLogger().hasHandlers():
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "app.log")

    handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

    logging.getLogger().addHandler(handler)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(level)
