"""ETL pipeline constants."""

from typing import Final
from app.core.data_dirs import ETL_DATA_DIR

FX_RATES_TO_BGN: Final[dict[str, float]] = {
    "BGN": 1.00,
    "EUR": 1.96,
    "USD": 1.80,
    "GBP": 2.30,
}

SUPPORTED_CURRENCIES: Final[frozenset[str]] = frozenset(FX_RATES_TO_BGN.keys())
ISO_DATE_FORMAT: Final[str] = "%Y-%m-%d"

DEFAULT_INPUT_FILE: Final[str] = str(ETL_DATA_DIR / "dirty_financial_data.csv")
DEFAULT_OUTPUT_JSON: Final[str] = str(ETL_DATA_DIR / "output_clean_data.json")
DEFAULT_QUALITY_REPORT: Final[str] = str(ETL_DATA_DIR / "data_quality_report.txt")
