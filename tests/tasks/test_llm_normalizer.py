"""Unit tests for LLM normalizer helpers."""

import pytest

from app.tasks.llm.models import ExtractedFinancialRecord
from app.tasks.llm.normalizer import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_record,
    validate_record,
)


def test_normalize_date_converts_dmy_to_iso():
    """DD.MM.YYYY dates become YYYY-MM-DD."""
    assert normalize_date("15.03.2024") == "2024-03-15"
    assert normalize_date("2024-03-15") == "2024-03-15"


def test_normalize_currency_maps_aliases():
    """Currency aliases map to supported ISO codes."""
    assert normalize_currency("EUR") == "EUR"
    assert normalize_currency("euro") == "EUR"
    assert normalize_currency("BGN") == "BGN"


def test_normalize_amount_parses_formatted_numbers():
    """Amount strings with commas parse to floats."""
    assert normalize_amount("5,916.60") == 5916.60
    assert normalize_amount(235.1) == 235.1


def test_thousands_unit_normalization_for_financial_table():
    """financial_table.txt values in k EUR normalize to absolute EUR amounts."""
    record = normalize_record(
        {
            "company_name": "BusinessGroup JSC",
            "document_date": "2024-04-05",
            "total_amount": 848.0,
            "currency": "EUR",
            "original_unit": "thousands_eur",
            "financial_metrics": {
                "q1_revenue_k_eur": 848.0,
                "q1_expenses_k_eur": 612.9,
                "q1_profit_k_eur": 235.1,
            },
        },
        source_document="financial_table.txt",
        extraction_method="mock",
    )
    assert record.total_amount == 848_000.0
    assert record.normalized_amount == 848_000.0
    assert record.original_unit == "thousands_eur"
    assert record.financial_metrics["q1_expenses_eur"] == 612_900.0
    assert record.financial_metrics["q1_profit_eur"] == 235_100.0
    assert record.normalization_note == "848.0 k EUR normalized to 848000 EUR"


def test_inline_thousands_metrics_scaled_consistently():
    """Generic revenue/expenses/profit metrics scale with thousands document units."""
    record = normalize_record(
        {
            "company_name": "BusinessGroup JSC",
            "document_date": "2024-04-05",
            "total_amount": 848.0,
            "currency": "EUR",
            "original_unit": "thousands_eur",
            "original_amount_text": "848.0 k EUR",
            "financial_metrics": {
                "revenue_eur": 848,
                "expenses_eur": 612.9,
                "profit_eur": 235.1,
                "ebitda_margin_pct": 18.5,
                "average_employees": 47,
            },
        },
        source_document="inline.txt",
        extraction_method="openai",
    )
    assert record.financial_metrics["revenue_eur"] == 848_000.0
    assert record.financial_metrics["expenses_eur"] == 612_900.0
    assert record.financial_metrics["profit_eur"] == 235_100.0
    assert record.financial_metrics["ebitda_margin_pct"] == 18.5
    assert record.financial_metrics["average_employees"] == 47


def test_million_unit_normalization_for_report():
    """Report revenue in millions normalizes to absolute EUR."""
    record = normalize_record(
        {
            "company_name": "InvestCapital LLC",
            "document_date": "2024-02-28",
            "total_amount": 12.5,
            "currency": "EUR",
            "original_unit": "million_eur",
            "detected_currencies": ["EUR", "BGN"],
            "financial_metrics": {
                "revenue_eur": 12_500_000,
                "operating_expenses_eur": 8_300_000,
                "net_profit_bgn": 3_200_000,
                "net_profit_eur": 1_640_000,
            },
        },
        source_document="report_excerpt.txt",
        extraction_method="mock",
    )
    assert record.total_amount == 12_500_000.0
    assert record.original_unit == "million_eur"
    assert record.financial_metrics["net_profit_bgn"] == 3_200_000


def test_inline_million_metrics_scaled_consistently():
    """Million-unit documents scale raw monetary metrics but not percentages."""
    record = normalize_record(
        {
            "company_name": "InvestCapital LLC",
            "document_date": "2024-02-28",
            "total_amount": 12.5,
            "currency": "EUR",
            "original_unit": "million_eur",
            "original_amount_text": "12.5 million EUR",
            "financial_metrics": {
                "revenue_eur": 12.5,
                "operating_expenses_eur": 8.3,
                "ebitda_margin_pct": 18.5,
            },
        },
        source_document="inline.txt",
        extraction_method="openai",
    )
    assert record.financial_metrics["revenue_eur"] == 12_500_000.0
    assert record.financial_metrics["operating_expenses_eur"] == pytest.approx(8_300_000.0)
    assert record.financial_metrics["ebitda_margin_pct"] == 18.5


def test_generates_normalization_note_from_original_and_normalized():
    """Auto-build normalization_note when original text and normalized amount exist."""
    record = normalize_record(
        {
            "company_name": "InvestCapital LLC",
            "document_date": "2024-02-28",
            "total_amount": 12.5,
            "currency": "EUR",
            "primary_currency": "EUR",
            "original_unit": "million_eur",
            "original_amount_text": "12.5 million EUR",
            "financial_metrics": {"revenue_eur": 12.5},
        },
        source_document="inline.txt",
        extraction_method="openai",
    )
    assert record.normalization_note == "12.5 million EUR normalized to 12500000 EUR"


def test_generates_normalization_note_for_thousands():
    """Thousands documents get a readable normalization note."""
    record = normalize_record(
        {
            "company_name": "BusinessGroup JSC",
            "document_date": "2024-04-05",
            "total_amount": 848.0,
            "currency": "EUR",
            "original_unit": "thousands_eur",
            "original_amount_text": "848.0 k EUR",
            "financial_metrics": {"revenue_eur": 848},
        },
        source_document="inline.txt",
        extraction_method="openai",
    )
    assert record.normalization_note == "848.0 k EUR normalized to 848000 EUR"


def test_preserves_existing_normalization_note():
    """Do not overwrite normalization_note when enrichment already set one."""
    record = normalize_record(
        {
            "company_name": "InvestCapital LLC",
            "document_date": "2024-02-28",
            "total_amount": 12.5,
            "currency": "EUR",
            "original_unit": "million_eur",
            "original_amount_text": "12.5 million EUR",
            "financial_metrics": {
                "revenue_eur": 12_500_000,
                "operating_expenses_eur": 8_300_000,
            },
        },
        source_document="report_excerpt.txt",
        extraction_method="mock",
    )
    assert "millions of EUR" in (record.normalization_note or "")


def test_mixed_currency_detection_adds_warning_not_fatal():
    """Multiple currencies produce a warning while core fields stay valid."""
    record = normalize_record(
        {
            "company_name": "InvestCapital LLC",
            "document_date": "2024-02-28",
            "total_amount": 12.5,
            "currency": "EUR",
            "detected_currencies": ["EUR", "BGN"],
            "financial_metrics": {
                "revenue_eur": 12_500_000,
                "net_profit_bgn": 3_200_000,
            },
        },
        source_document="report_excerpt.txt",
        extraction_method="mock",
    )
    assert record.detected_currencies == ["EUR", "BGN"]
    assert record.primary_currency == "EUR"
    assert any("multiple currencies" in err for err in record.validation_errors)
    assert record.total_amount == 12_500_000.0


def test_validate_record_flags_missing_fields():
    """Missing required fields produce validation_errors."""
    record = ExtractedFinancialRecord(
        company_name=None,
        document_date=None,
        total_amount=None,
        currency=None,
        expense_or_income_category=None,
        financial_metrics={},
        source_document="test.txt",
        extraction_method="mock",
    )
    errors = validate_record(record)
    assert "company_name is missing" in errors
    assert "currency is missing or unsupported" in errors


def test_normalize_record_builds_valid_invoice_record():
    """A complete raw dict normalizes without validation errors."""
    record = normalize_record(
        {
            "company_name": "TechnoSoft Ltd",
            "document_date": "15.03.2024",
            "total_amount": "5916.60",
            "currency": "EUR",
            "expense_or_income_category": "services",
            "financial_metrics": {"vat_eur": 986.10},
        },
        source_document="invoice.txt",
        extraction_method="mock",
    )
    assert record.document_date == "2024-03-15"
    assert record.total_amount == 5916.60
    assert record.original_unit == "absolute"
    assert record.validation_errors == []


def test_report_normalization_preserves_non_profit_metric_names():
    """Tax adjustment stays tax_adjustment_bgn and is not remapped to net_profit."""
    record = normalize_record(
        {
            "company_name": "Sample Co",
            "document_date": "2024-03-15",
            "total_amount": 500000,
            "currency": "BGN",
            "financial_metrics": {
                "tax_adjustment_bgn": "42,300",
            },
        },
        source_document="report_excerpt.txt",
        extraction_method="openai",
    )

    assert record.financial_metrics["tax_adjustment_bgn"] == 42300.0
    assert "net_profit_bgn" not in record.financial_metrics
