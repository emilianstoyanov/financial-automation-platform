"""Unit tests for ETL transformer functions."""

import pytest

from app.tasks.etl.transformers import (
    convert_to_bgn,
    is_missing,
    normalize_currency,
    parse_date,
    parse_numeric,
    record_fingerprint,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", True),
        (None, True),
        ("N/A", True),
        ("  n/a  ", True),
        ("COMP001", False),
        (123.45, False),
    ],
)
def test_is_missing(value, expected):
    """is_missing detects blanks and N/A-style placeholders."""
    assert is_missing(value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2024-06-01", "2024-06-01"),
        ("2024/04/10", "2024-04-10"),
        ("03-20-2024", "2024-03-20"),
        ("8/23/2024", "2024-08-23"),
        ("28/5/2024", "2024-05-28"),
        ("27/12/2024", "2024-12-27"),
        ("9/19/2024.", "2024-09-19"),
        ("28-05-2024", "2024-05-28"),
        ("15.03.2024", "2024-03-15"),
        ("", None),
        ("invalid", None),
        ("invalid-date", None),
        ("2024-13-40", None),
    ],
)
def test_parse_date(value, expected):
    """parse_date normalizes mixed inputs to ISO dates or None."""
    assert parse_date(value) == expected


def test_parse_date_iso_not_day_first():
    """ISO YYYY-MM-DD must never be reinterpreted as day-first."""
    assert parse_date("2024-06-01") == "2024-06-01"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("409695.23", 409695.23),
        ("69603", 69603.0),
        ("-13589.01", -13589.01),
        ("N/A", None),
        ("", None),
        ("312.927.93", None),
    ],
)
def test_parse_numeric(value, expected):
    """parse_numeric accepts valid numbers and rejects N/A or malformed values."""
    assert parse_numeric(value) == expected


def test_normalize_currency_defaults_to_bgn():
    """normalize_currency defaults empty values to BGN and rejects unknown codes."""
    assert normalize_currency("") == "BGN"
    assert normalize_currency("eur") == "EUR"
    assert normalize_currency("XYZ") is None


def test_convert_to_bgn():
    """convert_to_bgn applies fixed FX rates for EUR, USD, GBP, and BGN."""
    assert convert_to_bgn(100, "EUR") == 196.0
    assert convert_to_bgn(100, "USD") == 180.0
    assert convert_to_bgn(100, "GBP") == 230.0
    assert convert_to_bgn(100, "BGN") == 100.0


def test_record_fingerprint_is_stable():
    """Duplicate detection treats company_id and category case-insensitively."""
    key = record_fingerprint(
        "2024-08-23", "COMP004", 100.0, 50.0, "EUR", "Operations"
    )
    assert key == record_fingerprint(
        "2024-08-23", "comp004", 100.0, 50.0, "EUR", "operations"
    )
