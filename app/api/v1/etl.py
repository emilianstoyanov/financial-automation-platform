"""ETL API endpoints."""

from typing import Annotated
from app.tasks.etl.models import ETLResult
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.schemas.etl import ETLProcessResponse, QualityReportSchema
from app.services.etl_service import ETLApplicationService
from app.tasks.etl.exceptions import (
    ETLEmptyFileError,
    ETLFileNotFoundError,
    ETLInvalidFileTypeError,
    ETLProcessingError,
)

router = APIRouter(prefix="/etl", tags=["ETL"])


def _build_response(result: ETLResult) -> ETLProcessResponse:
    """Map ``ETLResult`` to API schema including a 10-record preview."""
    return ETLProcessResponse(
        status=result.status,
        quality_report=QualityReportSchema(**result.report.to_dict()),
        preview=result.preview,
        rejected_rows=result.rejected_rows_preview,
    )


@router.post(
    "/process-local-file",
    response_model=ETLProcessResponse,
    summary="Process local dirty financial CSV",
)
async def process_local_file() -> ETLProcessResponse:
    """Run ETL on the bundled sample CSV; returns status, quality report, and preview."""
    service = ETLApplicationService()

    try:
        result = service.process_local_file(persist=True)
    except ETLFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ETLProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return _build_response(result)


@router.post(
    "/upload",
    response_model=ETLProcessResponse,
    summary="Upload and process a financial CSV",
)
async def upload_csv(
        file: Annotated[
            UploadFile,
            File(description="Financial CSV file (.csv only)", media_type="text/csv"),
        ],
) -> ETLProcessResponse:
    """Accept a ``.csv`` upload, run ETL, persist outputs, return report and preview."""
    service = ETLApplicationService()

    try:
        content = await file.read()
        result = service.process_upload(file.filename, content, persist=True)
    except ETLInvalidFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ETLEmptyFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ETLProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return _build_response(result)
