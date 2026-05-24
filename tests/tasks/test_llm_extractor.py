"""Unit tests for mock/traditional LLM extraction."""

import json
from pathlib import Path

import pytest

from app.tasks.llm.data_extractor import TraditionalDataExtractor
from app.tasks.llm.llm_extractor import LLMDataExtractor, load_sample_document
from app.tasks.llm.normalizer import truncate_preview

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = (
    PROJECT_ROOT / "docs" / "assignment" / "Task_4_LLM_Data_Extraction" / "sample_documents"
)


@pytest.fixture
def mock_extractor():
    """LLM extractor without OpenAI API key (uses mock rules)."""
    return LLMDataExtractor(api_key="")


def test_mock_extracts_invoice_fields(mock_extractor):
    """invoice.txt yields TechnoSoft Ltd, 5916.60 EUR, date 2024-03-15."""
    text = load_sample_document("invoice.txt")
    record = mock_extractor.extract_from_document(text, source_document="invoice.txt")

    assert record.company_name == "TechnoSoft Ltd"
    assert record.document_date == "2024-03-15"
    assert record.total_amount == 5916.60
    assert record.currency == "EUR"
    assert record.original_unit == "absolute"
    assert record.extraction_method == "mock"
    assert record.validation_errors == []


def test_mock_extracts_financial_table_fields(mock_extractor):
    """financial_table.txt normalizes thousands of EUR to absolute amounts."""
    text = load_sample_document("financial_table.txt")
    record = mock_extractor.extract_from_document(text, source_document="financial_table.txt")

    assert record.company_name == "BusinessGroup JSC"
    assert record.document_date == "2024-04-05"
    assert record.currency == "EUR"
    assert record.total_amount == 848_000.0
    assert record.financial_metrics["q1_expenses_eur"] == 612_900.0
    assert record.financial_metrics["q1_profit_eur"] == 235_100.0
    assert record.original_unit == "thousands_eur"


def test_mock_extracts_report_excerpt_fields(mock_extractor):
    """report_excerpt.txt keeps EUR revenue and BGN net profit in metrics."""
    text = load_sample_document("report_excerpt.txt")
    record = mock_extractor.extract_from_document(text, source_document="report_excerpt.txt")

    assert record.company_name == "InvestCapital LLC"
    assert record.document_date == "2024-02-28"
    assert record.primary_currency == "EUR"
    assert "EUR" in record.detected_currencies
    assert "BGN" in record.detected_currencies
    assert record.total_amount == 12_500_000.0
    assert record.financial_metrics["revenue_eur"] == 12_500_000
    assert record.financial_metrics["operating_expenses_eur"] == 8_300_000
    assert record.financial_metrics["net_profit_bgn"] == 3_200_000
    assert any("multiple currencies" in err for err in record.validation_errors)


def test_traditional_extractor_parses_invoice():
    """Traditional regex extractor finds invoice total and company."""
    text = (SAMPLE_DIR / "invoice.txt").read_text(encoding="utf-8")
    record = TraditionalDataExtractor().extract_from_document(text, "invoice.txt")

    assert record.company_name == "TechnoSoft Ltd"
    assert record.total_amount == 5916.60
    assert record.extraction_method == "traditional"


def test_traditional_extractor_normalizes_financial_table_thousands():
    """Traditional path also scales k EUR table values to absolute EUR."""
    text = (SAMPLE_DIR / "financial_table.txt").read_text(encoding="utf-8")
    record = TraditionalDataExtractor().extract_from_document(text, "financial_table.txt")

    assert record.total_amount == 848_000.0
    assert record.financial_metrics["q1_profit_eur"] == 235_100.0


def test_process_sample_documents_writes_json_and_report(tmp_path, mock_extractor):
    """Batch run persists extracted_data.json with expected structure."""
    mock_extractor._output_json = tmp_path / "extracted_data.json"
    mock_extractor._comparison_report = tmp_path / "comparison_report.md"

    result = mock_extractor.process_sample_documents(persist=True)

    assert result.total_documents == 3
    payload = json.loads((tmp_path / "extracted_data.json").read_text(encoding="utf-8"))
    assert "metadata" in payload
    assert "documents" in payload
    assert payload["metadata"]["total_documents"] == 3
    doc = payload["documents"][1]
    assert doc["normalized_amount"] == 848_000.0
    assert "original_unit" in doc
    report = (tmp_path / "comparison_report.md").read_text(encoding="utf-8")
    assert "Mismatch note" in report or "normalization" in report.lower()


def test_truncate_preview_limits_to_500_characters():
    """Preview helper caps text at 500 characters."""
    assert len(truncate_preview("word " * 200, 500)) == 500
