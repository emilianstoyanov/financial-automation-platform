"""Task 1 ETL focused unit tests."""

from pathlib import Path

import pandas as pd
import pytest

from app.tasks.etl.pipeline import ETLPipelineService
from app.tasks.etl.transformers import convert_to_bgn, parse_date, parse_numeric


@pytest.fixture
def pipeline() -> ETLPipelineService:
    return ETLPipelineService()


def test_date_normalization(pipeline: ETLPipelineService):
    """European date 28/5/2024 is stored as ISO 2024-05-28."""
    record, reason = pipeline._process_row(
        {
            "date": "28/5/2024",
            "company_id": "COMP001",
            "revenue": "100",
            "expenses": "20",
            "currency": "BGN",
            "category": "Sales",
        }
    )
    assert reason is None
    assert record is not None
    assert record.date == "2024-05-28"


def test_numeric_validation_rejects_invalid_values(pipeline: ETLPipelineService):
    """Malformed revenue marks the row invalid_numeric; parse_numeric rejects N/A."""
    _, reason = pipeline._process_row(
        {
            "date": "1/1/2024",
            "company_id": "COMP001",
            "revenue": "312.927.93",
            "expenses": "10",
            "currency": "BGN",
            "category": "Sales",
        }
    )
    assert reason is not None
    assert reason.startswith("invalid_numeric_value")

    assert parse_numeric("N/A") is None
    assert parse_numeric("409695.23") == 409695.23


def test_profit_calculation(pipeline: ETLPipelineService):
    """profit equals revenue minus expenses for a valid BGN row."""
    record, reason = pipeline._process_row(
        {
            "date": "2/14/2024",
            "company_id": "COMP002",
            "revenue": "100",
            "expenses": "30",
            "currency": "BGN",
            "category": "Operations",
        }
    )
    assert reason is None
    assert record is not None
    assert record.profit == 70.0


def test_currency_conversion_to_bgn(pipeline: ETLPipelineService):
    """EUR amounts are converted to BGN using the fixed rate table."""
    record, reason = pipeline._process_row(
        {
            "date": "8/23/2024",
            "company_id": "COMP004",
            "revenue": "100",
            "expenses": "50",
            "currency": "EUR",
            "category": "Operations",
        }
    )
    assert reason is None
    assert record is not None
    assert record.currency == "BGN"
    assert record.original_currency == "EUR"
    assert record.revenue == convert_to_bgn(100, "EUR")
    assert record.expenses == convert_to_bgn(50, "EUR")
    assert record.profit == round(record.revenue - record.expenses, 2)


def test_duplicate_removal(tmp_path: Path):
    """Identical rows produce one cleaned record and one duplicate removed."""
    csv_path = tmp_path / "dup.csv"
    pd.DataFrame(
        [
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
        ]
    ).to_csv(csv_path, index=False)

    result = ETLPipelineService(input_path=csv_path).run(persist=False)
    assert result.report.duplicate_rows_removed == 1
    assert result.report.cleaned_rows == 1


def test_invalid_rows_are_removed(tmp_path: Path):
    """Only the single valid row remains after bad date and invalid revenue."""
    csv_path = tmp_path / "invalid.csv"
    pd.DataFrame(
        [
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "",
                "company_id": "COMP002",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "1/2/2024",
                "company_id": "COMP003",
                "revenue": "N/A",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
        ]
    ).to_csv(csv_path, index=False)

    result = ETLPipelineService(input_path=csv_path).run(persist=False)
    assert result.report.total_rows == 3
    assert result.report.cleaned_rows == 1
    assert len(result.records) == 1
    assert result.records[0].company_id == "COMP001"


def test_quality_report_counters(tmp_path: Path):
    """Assert each report counter for a mix of valid, duplicate, bad date, and bad numeric rows."""
    csv_path = tmp_path / "report.csv"
    pd.DataFrame(
        [
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "",
                "company_id": "COMP002",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "1/3/2024",
                "company_id": "COMP003",
                "revenue": "bad",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
        ]
    ).to_csv(csv_path, index=False)

    report = ETLPipelineService(input_path=csv_path).run(persist=False).report
    assert report.total_rows == 4
    assert report.cleaned_rows == 1
    assert report.removed_rows == 3
    assert report.duplicate_rows_removed == 1
    assert report.invalid_date_rows == 1
    assert report.invalid_numeric_rows == 1
    assert report.missing_value_rows == 0


def test_rejected_rows_include_reason_and_original_data(tmp_path: Path):
    """Rejected rows expose CSV line number, reason, and original row values."""
    csv_path = tmp_path / "rejected.csv"
    pd.DataFrame(
        [
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "1/2/2024",
                "company_id": "COMP002",
                "revenue": "bad",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "1/1/2024",
                "company_id": "COMP001",
                "revenue": "10",
                "expenses": "4",
                "currency": "BGN",
                "category": "Sales",
            },
        ]
    ).to_csv(csv_path, index=False)

    result = ETLPipelineService(input_path=csv_path).run(persist=False)
    assert len(result.rejected_rows) == 2
    assert result.rejected_rows[0].row_number == 3
    assert result.rejected_rows[0].reason.startswith("invalid_numeric_value")
    assert result.rejected_rows[0].original_data["company_id"] == "COMP002"
    assert result.rejected_rows[1].reason.startswith("duplicate_row")


def test_parse_date_normalization_examples():
    """Common US and European date strings map to expected ISO values."""
    assert parse_date("8/23/2024") == "2024-08-23"
    assert parse_date("27/12/2024") == "2024-12-27"
