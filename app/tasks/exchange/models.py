"""Exchange rate domain models."""

from dataclasses import asdict, dataclass


@dataclass
class ExchangeRatesResult:
    """Fetched or cached rates expressed as target currency per 1 BGN (API native)."""

    base: str
    rates_per_bgn: dict[str, float]
    bgn_per_unit: dict[str, float]
    timestamp: str
    cached: bool
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConversionResult:
    """Result of converting an amount between two currencies."""

    from_currency: str
    to_currency: str
    original_amount: float
    converted_amount: float
    rate: float
    source: str
    cached: bool
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)
