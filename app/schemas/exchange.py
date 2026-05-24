"""Exchange rate API schemas."""

from pydantic import BaseModel, Field


class ExchangeRatesResponse(BaseModel):
    """Current exchange rates against BGN."""

    base: str
    rates: dict[str, float] = Field(
        description="BGN per 1 unit of currency (e.g. how many BGN for 1 EUR)",
    )
    cached: bool
    source: str
    timestamp: str


class ConversionResponse(BaseModel):
    """Currency conversion result."""

    from_currency: str
    to_currency: str
    original_amount: float
    converted_amount: float
    rate: float
    source: str
    cached: bool
    timestamp: str
