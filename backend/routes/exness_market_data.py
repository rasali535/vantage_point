"""Read-only Exness market-data endpoints for the initial three-symbol rollout."""
from fastapi import APIRouter, HTTPException, Query

from markets.providers.exness import (
    ExnessAPIError,
    ExnessConfigurationError,
    ExnessReadOnlyClient,
)

router = APIRouter()
INITIAL_INSTRUMENTS = {"XAUUSD", "EURUSD", "GBPUSD"}


def _client():
    try:
        return ExnessReadOnlyClient()
    except ExnessConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/ticks")
async def exness_ticks(
    instruments: str = Query(default="XAUUSD,EURUSD,GBPUSD", description="Comma-separated initial rollout symbols")
):
    requested = [item.strip().upper() for item in instruments.split(",") if item.strip()]
    if not requested or len(requested) > 3 or len(set(requested)) != len(requested) or not set(requested).issubset(INITIAL_INSTRUMENTS):
        raise HTTPException(status_code=400, detail="Only unique XAUUSD, EURUSD and GBPUSD symbols are enabled.")
    try:
        ticks = await _client().get_ticks(requested)
        return {
            "provider": "exness",
            "read_only": True,
            "execution_enabled": False,
            "requested": requested,
            "received": len(ticks),
            "ticks": ticks,
        }
    except ExnessConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExnessAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/candles")
async def exness_candles(
    instrument: str = Query(..., min_length=1, max_length=11),
    timeframe: str = Query(default="M15"),
    count: int = Query(default=100, ge=1, le=500),
    price_type: str = Query(default="both"),
):
    instrument = instrument.strip().upper()
    if instrument not in INITIAL_INSTRUMENTS:
        raise HTTPException(status_code=400, detail="Only XAUUSD, EURUSD and GBPUSD are enabled.")
    try:
        candles = await _client().get_candles(instrument, timeframe, count, price_type)
        return {
            "provider": "exness",
            "read_only": True,
            "execution_enabled": False,
            "instrument": instrument,
            "timeframe": timeframe,
            "price_type": price_type,
            "count": len(candles),
            "candles": candles,
        }
    except ExnessConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExnessAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
