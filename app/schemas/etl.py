"""ETL API schemas."""

from pydantic import BaseModel, Field


class QualityReportSchema(BaseModel):
    """Data quality metrics."""

    total_rows: int
    cleaned_rows: int
    removed_rows: int
    duplicate_rows_removed: int
    invalid_numeric_rows: int
    invalid_date_rows: int
    missing_value_rows: int


class RejectedRowSchema(BaseModel):
    """One rejected CSV row with reason and original values."""

    row_number: int
    reason: str
    original_data: dict[str, str]


class ETLProcessResponse(BaseModel):
    """Response for local file ETL processing."""

    status: str = Field(..., examples=["success"])
    quality_report: QualityReportSchema
    preview: list[dict] = Field(
        ...,
        description="First 10 cleaned records",
    )
    rejected_rows: list[RejectedRowSchema] = Field(
        default_factory=list,
        description="Rows rejected during cleaning with reason and original data",
    )
