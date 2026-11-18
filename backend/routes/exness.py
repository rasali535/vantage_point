"""Read-only Exness connection diagnostics."""
import logging
import os

from fastapi import APIRouter, HTTPException

from markets.providers.exness import (
    ExnessAPIError,
    ExnessConfigurationError,
    ExnessReadOnlyClient,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status")
async def exness_status():
    configured = all(os.getenv(name, "").strip() for name in (
        "EXN_API_KEY", "EXN_PRIVATE_KEY", "EXN_ACCOUNT_ID", "EXN_DISCOVERY_BASE_URL"
    ))
    return {
        "provider": "exness",
        "configured": configured,
        "read_only": os.getenv("EXN_READ_ONLY", "true").strip().lower() == "true",
        "execution_enabled": False,
        "capabilities": ["account_read", "instrument_discovery"],
    }


@router.get("/connection-test")
async def exness_connection_test():
    try:
        client = ExnessReadOnlyClient()
        account = await client.get_account()
        instruments = await client.get_instruments()
        return {
            "provider": "exness",
            "connected": True,
            "read_only": True,
            "execution_enabled": False,
            "account_check": "passed",
            "instrument_count": len(instruments),
            "instruments": instruments,
            "account_summary": {
                key: account.get(key)
                for key in ("currency", "leverage", "trade_mode")
                if key in account
            },
        }
    except ExnessConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ExnessAPIError as exc:
        logger.warning("exness_read_only_connection_failed error=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("exness_read_only_connection_unexpected error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Exness read-only connection test failed. Check backend logs for the error type.",
        ) from exc
