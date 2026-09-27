import logging
from config import LOG_FILE

logger = logging.getLogger("accounting")

logger.setLevel(logging.INFO)

handler = logging.FileHandler(
    LOG_FILE,
    encoding="utf-8"
)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)

handler.setFormatter(formatter)

logger.addHandler(handler)