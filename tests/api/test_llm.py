"""LLM extraction API endpoint tests."""

from unittest.mock import patch

from app.tasks.llm.models import ExtractedFinancialRecord, ExtractionBatchResult


def _sample_record(model: str | None = "mock") -> ExtractedFinancialRecord:
    return ExtractedFinancialRecord(
        company_name="TechnoSoft Ltd",
        document_date="2024-03-15",
        total_amount=5916.60,
        currency="EUR",
        expense_or_income_category="services",
        financial_metrics={"vat_eur": 986.10},
        source_document="invoice.txt",
        extraction_method="mock",
        model=model,
    )


def _sample_batch() -> ExtractionBatchResult:
    return ExtractionBatchResult(
        status="success",
        extraction_method="mock",
        model="mock",
        documents=[_sample_record()],
    )


def test_process_sample_documents_endpoint(client):
    """GET process-sample-documents returns status and extracted preview."""
    with patch(
        "app.api.v1.llm.LLMApplicationService.process_sample_documents",
        return_value=_sample_batch(),
    ):
        response = client.get("/api/v1/llm/process-sample-documents")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["extraction_method"] == "mock"
    assert data["model"] == "mock"
    assert data["total_documents"] == 1


def test_extract_endpoint(client):
    """POST extract accepts text and returns structured financial data."""
    with patch(
        "app.api.v1.llm.LLMApplicationService.extract_from_text",
        return_value=_sample_record(),
    ):
        response = client.post(
            "/api/v1/llm/extract",
            json={"text": "Company: TechnoSoft Ltd\nTOTAL AMOUNT DUE: 5916.60 EUR"},
        )

    assert response.status_code == 200
    assert response.json()["total_documents"] == 1
    assert response.json()["extracted_results"][0]["company_name"] == "TechnoSoft Ltd"


def test_extract_rejects_empty_text(client):
    """POST extract returns 422 for empty text body."""
    response = client.post("/api/v1/llm/extract", json={"text": ""})
    assert response.status_code == 422


def test_extract_accepts_optional_model(client):
    """POST extract forwards an optional OpenAI model override."""
    with patch(
        "app.api.v1.llm.LLMApplicationService.extract_from_text",
        return_value=_sample_record(),
    ) as extract_mock:
        response = client.post(
            "/api/v1/llm/extract",
            json={"text": "Company: TechnoSoft Ltd", "model": "gpt-4.1"},
        )

    assert response.status_code == 200
    extract_mock.assert_called_once()
    assert extract_mock.call_args.kwargs["model"] == "gpt-4.1"


def test_extract_returns_selected_model(client):
    """POST extract includes resolved model at top level and in each document."""
    record = _sample_record(model="gpt-4.1-mini")
    record.extraction_method = "openai"

    with patch(
        "app.api.v1.llm.LLMApplicationService.extract_from_text",
        return_value=record,
    ):
        response = client.post(
            "/api/v1/llm/extract",
            json={"text": "Company: TechnoSoft Ltd", "model": "gpt-4.1-mini"},
        )

    data = response.json()
    assert response.status_code == 200
    assert data["model"] == "gpt-4.1-mini"
    assert data["extracted_results"][0]["model"] == "gpt-4.1-mini"


def test_extract_rejects_unknown_model(client):
    """POST extract returns 422 for unsupported model names."""
    response = client.post(
        "/api/v1/llm/extract",
        json={"text": "Company: Example", "model": "gpt-5-ultra"},
    )
    assert response.status_code == 422
