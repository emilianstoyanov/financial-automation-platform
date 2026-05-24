"""Pydantic schemas for LLM extraction API."""

from typing import Literal

from pydantic import BaseModel, Field

DashboardOpenAIModel = Literal["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"]


class ExtractTextRequest(BaseModel):
    """Request body for extracting structured data from free text."""

    text: str = Field(min_length=1, description="Financial document text")
    model: DashboardOpenAIModel | None = Field(
        default=None,
        description="OpenAI model override; uses OPENAI_MODEL from env when omitted",
    )


class LLMProcessResponse(BaseModel):
    """Response for an LLM extraction run."""

    status: str
    extraction_method: str
    model: str | None = None
    total_documents: int
    extracted_results: list[dict] = Field(
        default_factory=list,
        description="Preview of extracted records (up to 10)",
    )
    errors: list[str] = Field(default_factory=list)
