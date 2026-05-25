"""Pure transformation helpers for the ETL pipeline."""

import re
from datetime import datetime
from typing import Any
from dateutil import parser as date_parser
from app.tasks.etl.constants import FX_RATES_TO_BGN, ISO_DATE_FORMAT, SUPPORTED_CURRENCIES

_MISSING_VALUES = frozenset({"", "nan", "none", "n/a", "na", "null"})


def is_missing(value: Any) -> bool:
    """True for None, blank strings, and placeholders such as N/A."""
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in _MISSING_VALUES


_ISO_DATE_LIKE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")

_STRICT_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
)

_EXTRA_DATE_FORMATS = (
    "%d/%m/%Y",
)


def _parse_dmy_dash_unambiguous(text: str) -> datetime | None:
    """Parse ``%d-%m-%Y`` only when the first segment is clearly a day (> 12)."""
    parts = text.split("-")
    if len(parts) != 3 or len(parts[2]) != 4:
        return None
    try:
        first, second, year = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if first <= 12:
        return None
    if not (1 <= second <= 12):
        return None
    try:
        return datetime(year, second, first)
    except ValueError:
        return None


def _try_strptime_formats(text: str, formats: tuple[str, ...]) -> datetime | None:
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_date(value: Any) -> str | None:
    """Normalize mixed date strings to ISO ``YYYY-MM-DD``; None if unparseable."""
    if is_missing(value):
        return None

    text = str(value).strip().rstrip(".")
    if not text:
        return None

    parsed = _try_strptime_formats(text, _STRICT_DATE_FORMATS)
    if parsed is None:
        parsed = _parse_dmy_dash_unambiguous(text)
    if parsed is None:
        parsed = _try_strptime_formats(text, _EXTRA_DATE_FORMATS)
    if parsed is not None:
        return parsed.strftime(ISO_DATE_FORMAT)

    if _ISO_DATE_LIKE.match(text):
        return None

    try:
        parsed = date_parser.parse(text, dayfirst=True)
    except (ValueError, TypeError, OverflowError):
        return None

    return parsed.strftime(ISO_DATE_FORMAT)


def parse_numeric(value: Any) -> float | None:
    """Parse revenue/expenses; None for missing, N/A, or malformed values (e.g. ``312.927.93``)."""
    if is_missing(value):
        return None

    text = str(value).strip().replace(" ", "")
    if not text:
        return None

    upper = text.upper()
    if upper in {"N/A", "NA", "NAN"}:
        return None

    # Reject malformed values such as 312.927.93 (multiple dot groups)
    if text.count(".") > 1:
        return None

    normalized = text.replace(",", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def normalize_currency(value: Any) -> str | None:
    """Return uppercase EUR/USD/GBP/BGN code; BGN when empty; None if unsupported."""
    if is_missing(value):
        return "BGN"

    code = str(value).strip().upper()
    if code in SUPPORTED_CURRENCIES:
        return code
    return None


def convert_to_bgn(amount: float, currency: str) -> float:
    """Multiply ``amount`` by the fixed ``FX_RATES_TO_BGN`` rate; round to 2 decimals."""
    rate = FX_RATES_TO_BGN[currency]
    return round(amount * rate, 2)


def normalize_category(value: Any) -> str:
    """Normalize category text, fixing common encoding typos."""
    if is_missing(value):
        return "Unknown"

    text = str(value).strip()
    replacements = {
        "?arketing": "Marketing",
        "?perations": "Operations",
    }
    return replacements.get(text, text)


def record_fingerprint(
        date: str,
        company_id: str,
        revenue: float,
        expenses: float,
        currency: str,
        category: str,
) -> tuple:
    """Build a hashable key for duplicate detection."""
    return (
        date,
        company_id.strip().upper(),
        round(revenue, 2),
        round(expenses, 2),
        currency,
        category.strip().lower(),
    )
