"""Health check response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check API response."""

    status: str = Field(..., examples=["healthy", "degraded"])
    environment: str = Field(..., examples=["development"])
    service: str
    database: str = Field(..., examples=["connected"])
    version: str = Field(default="0.1.0")
