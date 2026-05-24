"""Exchange rate API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.exchange import ConversionResponse, ExchangeRatesResponse
from app.services.exchange_service import ExchangeApplicationService
from app.tasks.exchange.exceptions import (
    ExchangeAPIError,
    ExchangeCurrencyNotFoundError,
    ExchangeError,
    ExchangeInvalidResponseError,
    ExchangeNetworkError,
    ExchangeTimeoutError,
)

router = APIRouter(prefix="/exchange", tags=["Exchange"])


@router.get("/rates", response_model=ExchangeRatesResponse)
async def get_exchange_rates() -> ExchangeRatesResponse:
    """Return EUR/USD/GBP as BGN per unit; serves cache when younger than one hour."""
    service = ExchangeApplicationService()

    try:
        result = service.get_rates()
    except (ExchangeTimeoutError, ExchangeNetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (ExchangeAPIError, ExchangeInvalidResponseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ExchangeCurrencyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ExchangeRatesResponse(
        base=result.base,
        rates=result.bgn_per_unit,
        cached=result.cached,
        source=result.source,
        timestamp=result.timestamp,
    )


@router.get("/convert", response_model=ConversionResponse)
async def convert_currency(
        from_currency: str = Query(..., min_length=3, max_length=3),
        to_currency: str = Query(..., min_length=3, max_length=3),
        amount: float = Query(..., ge=0),
) -> ConversionResponse:
    """Convert ``amount`` between BGN, EUR, USD, or GBP; includes rate, source, and cache metadata."""
    service = ExchangeApplicationService()

    try:
        result = service.convert(from_currency, to_currency, amount)
    except ExchangeCurrencyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ExchangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (ExchangeTimeoutError, ExchangeNetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (ExchangeAPIError, ExchangeInvalidResponseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ConversionResponse(**result.to_dict())
