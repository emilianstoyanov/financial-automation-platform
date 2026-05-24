"""Local data directory layout and initialization."""

from pathlib import Path

DATA_DIR = Path("data")
ETL_DATA_DIR = DATA_DIR / "etl"
EXCHANGE_DATA_DIR = DATA_DIR / "exchange"
SCRAPING_DATA_DIR = DATA_DIR / "scraping"
LLM_DATA_DIR = DATA_DIR / "llm"

_TASK_DATA_DIRS = (
    ETL_DATA_DIR,
    EXCHANGE_DATA_DIR,
    SCRAPING_DATA_DIR,
    LLM_DATA_DIR,
)


def ensure_data_directories() -> None:
    """Create the local data folder tree if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for directory in _TASK_DATA_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
