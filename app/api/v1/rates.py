"""Exchange rate history API endpoints (Task 5)."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.schemas.rates import RateEntryResponse, RatesHistoryResponse, RatesLatestResponse, RatesRefreshResponse
from app.services.rates_history_service import RatesHistoryApplicationService

router = APIRouter(prefix="/rates", tags=["Rates History"])


def _to_rate_entries(data: dict) -> list[RateEntryResponse]:
    return [RateEntryResponse(**item) for item in data.get("rates", [])]


@router.get("", response_model=RatesLatestResponse)
async def get_latest_rates(db: DbSession) -> RatesLatestResponse:
    """Return latest stored BGN-based rates with daily change from SQLite."""
    service = RatesHistoryApplicationService(db)
    data = service.get_latest_with_changes()
    return RatesLatestResponse(
        base_currency=data["base_currency"],
        rates=_to_rate_entries(data),
        last_refresh_at=data.get("last_refresh_at"),
        source=data.get("source"),
        last_inserted_count=data.get("last_inserted_count"),
        last_updated_count=data.get("last_updated_count"),
        errors=data.get("errors", []),
    )


@router.get("/history", response_model=RatesHistoryResponse)
async def get_rates_history(
    db: DbSession,
    days: int = Query(7, ge=1, le=365),
) -> RatesHistoryResponse:
    """Return historical exchange rates for the last ``days`` days."""
    service = RatesHistoryApplicationService(db)
    data = service.get_history(days=days)
    return RatesHistoryResponse(
        base_currency=data["base_currency"],
        days=data["days"],
        history=[RateEntryResponse(**item) for item in data["history"]],
        last_refresh_at=data.get("last_refresh_at"),
        source=data.get("source"),
    )


@router.post("/refresh", response_model=RatesRefreshResponse)
async def refresh_rates(db: DbSession) -> RatesRefreshResponse:
    """Fetch live rates, persist to SQLite, and return latest snapshot."""
    service = RatesHistoryApplicationService(db)

    try:
        refresh_result = service.refresh()
        data = service.build_response_from_refresh(refresh_result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rates refresh failed: {exc}",
        ) from exc

    return RatesRefreshResponse(
        base_currency=data["base_currency"],
        rates=_to_rate_entries(data),
        last_refresh_at=data.get("last_refresh_at"),
        source=data.get("source"),
        last_inserted_count=refresh_result.inserted_count,
        last_updated_count=refresh_result.updated_count,
        inserted_count=refresh_result.inserted_count,
        updated_count=refresh_result.updated_count,
        errors=data.get("errors", refresh_result.errors),
    )
