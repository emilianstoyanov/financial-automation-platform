"""Health check response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check API response."""

    status: str = Field(..., examples=["healthy", "degraded"])
    environment: str = Field(..., examples=["development"])
    service: str
    database: str = Field(..., examples=["connected"])
    version: str = Field(default="0.1.0")
    news_scheduler_enabled: bool = Field(
        default=False,
        description="Whether background RSS refresh is enabled",
    )
    news_scheduler_interval_minutes: int = Field(
        default=1440,
        ge=1,
        description="Minutes between scheduled RSS refreshes",
    )
    rates_scheduler_enabled: bool = Field(
        default=False,
        description="Whether background exchange rate history refresh is enabled",
    )
    rates_scheduler_interval_minutes: int = Field(
        default=1440,
        ge=1,
        description="Minutes between scheduled exchange rate refreshes",
    )
