"""LLM-assisted data extraction API endpoints."""

from fastapi import APIRouter, HTTPException, status
from app.services.llm_service import LLMApplicationService
from app.schemas.llm import ExtractTextRequest, LLMProcessResponse
from app.tasks.llm.exceptions import LLMAPIError, LLMDocumentNotFoundError
from app.tasks.llm.models import ExtractionBatchResult, ExtractedFinancialRecord

router = APIRouter(prefix="/llm", tags=["LLM"])


def _build_batch_response(result: ExtractionBatchResult) -> LLMProcessResponse:
    """Map batch extraction result to API response."""
    return LLMProcessResponse(
        status=result.status,
        extraction_method=result.extraction_method,
        model=result.model,
        total_documents=result.total_documents,
        extracted_results=result.preview,
        errors=result.errors,
    )


def _build_single_response(record: ExtractedFinancialRecord) -> LLMProcessResponse:
    """Map a single extraction record to API response."""
    method = record.extraction_method
    return LLMProcessResponse(
        status="success" if not record.validation_errors else "partial",
        extraction_method=method,
        model=record.model,
        total_documents=1,
        extracted_results=[record.to_dict()],
        errors=record.validation_errors,
    )


@router.get(
    "/process-sample-documents",
    response_model=LLMProcessResponse,
    summary="Extract data from sample financial documents",
)
async def process_sample_documents() -> LLMProcessResponse:
    """Process all Task 4 sample documents; writes JSON and comparison report."""
    service = LLMApplicationService()

    try:
        result = service.process_sample_documents(persist=True)
    except LLMDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _build_batch_response(result)


@router.post(
    "/extract",
    response_model=LLMProcessResponse,
    summary="Extract structured data from document text",
)
async def extract_text(body: ExtractTextRequest) -> LLMProcessResponse:
    """Extract company, date, amount, currency, and metrics from provided text."""
    service = LLMApplicationService()

    try:
        record = service.extract_from_text(body.text, model=body.model)
    except LLMAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return _build_single_response(record)
