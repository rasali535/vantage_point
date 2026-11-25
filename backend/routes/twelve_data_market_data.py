"""Read-only Twelve Data diagnostics; these routes cannot create paper or broker orders."""
from fastapi import APIRouter, HTTPException, Query

from markets.providers.twelve_data import (
    TwelveDataAPIError,
    TwelveDataConfigurationError,
    TwelveDataReadOnlyClient,
)

router = APIRouter()


def _client() -> TwelveDataReadOnlyClient:
    try:
        return TwelveDataReadOnlyClient()
    except TwelveDataConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/quote")
async def twelve_data_quote(
    symbol: str = Query(..., min_length=3, max_length=7),
):
    try:
        quote = await _client().get_quote(symbol)
        return quote
    except TwelveDataConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TwelveDataAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/candles")
async def twelve_data_candles(
    symbol: str = Query(..., min_length=3, max_length=7),
    interval: str = Query(default="15min"),
    outputsize: int = Query(default=120, ge=1, le=500),
):
    try:
        candles = await _client().get_candles(symbol, interval, outputsize)
        latest = candles[-1]
        return {
            "provider": "twelve_data",
            "symbol": symbol.strip().upper(),
            "interval": interval.strip().lower(),
            "requested": outputsize,
            "received": len(candles),
            "sufficient_history": len(candles) >= 100,
            "latest_candle": latest["datetime"],
            "candles": candles,
            "read_only": True,
            "execution_enabled": False,
        }
    except TwelveDataConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TwelveDataAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
