"""Unit tests for ETL pipeline service."""

import json
from pathlib import Path

import pandas as pd
import pytest

from app.tasks.etl.exceptions import ETLFileNotFoundError
from app.tasks.etl.pipeline import ETLPipelineService


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    path = tmp_path / "sample.csv"
    pd.DataFrame(
        [
            {
                "date": "8/23/2024",
                "company_id": "COMP004",
                "revenue": "100",
                "expenses": "40",
                "currency": "EUR",
                "category": "Operations",
            },
            {
                "date": "",
                "company_id": "COMP001",
                "revenue": "50",
                "expenses": "10",
                "currency": "BGN",
                "category": "Sales",
            },
            {
                "date": "8/23/2024",
                "company_id": "COMP004",
                "revenue": "100",
                "expenses": "40",
                "currency": "EUR",
                "category": "Operations",
            },
            {
                "date": "1/1/2024",
                "company_id": "COMP002",
                "revenue": "N/A",
                "expenses": "10",
                "currency": "BGN",
                "category": "Ops",
            },
        ]
    ).to_csv(path, index=False)
    return path


def test_pipeline_processes_valid_rows_and_report(tmp_path: Path, sample_csv: Path):
    """End-to-end run on a mixed CSV fixture and verify BGN conversion plus written outputs."""
    output_json = tmp_path / "out.json"
    report_path = tmp_path / "report.txt"

    service = ETLPipelineService(
        input_path=sample_csv,
        output_json_path=output_json,
        report_path=report_path,
    )
    result = service.run(persist=True)

    assert result.status == "success"
    assert result.report.total_rows == 4
    assert result.report.cleaned_rows == 1
    assert result.report.duplicate_rows_removed == 1
    assert result.report.invalid_date_rows == 1
    assert result.report.missing_value_rows == 1

    record = result.records[0]
    assert record.currency == "BGN"
    assert record.original_currency == "EUR"
    assert record.revenue == 196.0
    assert record.expenses == 78.4
    assert record.profit == 117.6

    assert output_json.exists()
    assert report_path.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert len(saved["records"]) == 1


def test_pipeline_raises_when_file_missing(tmp_path: Path):
    """Pipeline raises ETLFileNotFoundError when the input CSV does not exist."""
    service = ETLPipelineService(input_path=tmp_path / "missing.csv")
    with pytest.raises(ETLFileNotFoundError):
        service.run(persist=False)
