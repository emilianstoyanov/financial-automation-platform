"""ETL API endpoint tests."""

import io
import pandas as pd
from pathlib import Path
from app.services.etl_service import ETLApplicationService


def _valid_csv_bytes() -> bytes:
    buffer = io.StringIO()
    pd.DataFrame(
        [
            {
                "date": "2/14/2024",
                "company_id": "COMP002",
                "revenue": "100",
                "expenses": "30",
                "currency": "BGN",
                "category": "Operations",
            }
        ]
    ).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def test_process_local_file_endpoint(client):
    """POST process-local-file returns success and writes JSON and quality report under data/etl/."""
    response = client.post("/api/v1/etl/process-local-file")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["quality_report"]["total_rows"] > 0
    assert data["quality_report"]["cleaned_rows"] > 0
    assert len(data["preview"]) <= 10

    assert Path("data/etl/output_clean_data.json").exists()
    assert Path("data/etl/data_quality_report.txt").exists()


def test_process_local_file_not_found(client, monkeypatch):
    """Local-file endpoint returns 404 when the configured CSV path is missing."""
    def missing_file_service():
        return ETLApplicationService(input_path="data/etl/nonexistent.csv")

    monkeypatch.setattr("app.api.v1.etl.ETLApplicationService", missing_file_service)

    response = client.post("/api/v1/etl/process-local-file")
    assert response.status_code == 404


def test_upload_endpoint_success(client, tmp_path, monkeypatch):
    """Upload succeeds and writes outputs to overridden paths (isolated from repo data/)."""
    output_json = tmp_path / "output_clean_data.json"
    report_path = tmp_path / "data_quality_report.txt"

    monkeypatch.setattr(
        "app.api.v1.etl.ETLApplicationService",
        lambda: ETLApplicationService(
            output_json_path=output_json,
            report_path=report_path,
        ),
    )

    response = client.post(
        "/api/v1/etl/upload",
        files={"file": ("upload.csv", _valid_csv_bytes(), "text/csv")},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["quality_report"]["cleaned_rows"] == 1
    assert len(data["preview"]) == 1
    assert data["preview"][0]["profit"] == 70.0
    assert "rejected_rows" in data
    assert isinstance(data["rejected_rows"], list)
    assert output_json.exists()
    assert report_path.exists()


def test_upload_endpoint_rejects_non_csv(client):
    """Upload rejects non-.csv files with HTTP 400."""
    response = client.post(
        "/api/v1/etl/upload",
        files={"file": ("data.txt", b"not,a,csv", "text/plain")},
    )
    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_upload_endpoint_rejects_empty_file(client):
    """Upload rejects whitespace-only CSV content with HTTP 400."""
    response = client.post(
        "/api/v1/etl/upload",
        files={"file": ("empty.csv", b"   ", "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
