from datetime import datetime, timezone
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from agents.kraken import KrakenAgent
from agents.reasoning import boardroom
from agents.whipsaw_protection import whipsaw_protection
from database import get_database

router = APIRouter()
_kraken_agent = None


def get_kraken_agent() -> KrakenAgent:
    global _kraken_agent
    if _kraken_agent is None:
        _kraken_agent = KrakenAgent()
    return _kraken_agent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document


@router.get("/status")
async def get_trading_status():
    db = await get_database()
    history = await db.trading_ledger.find().sort("timestamp", -1).limit(20).to_list(length=20)

    balance = None
    account_status = "disabled"
    agent = get_kraken_agent()
    if agent.account_reads_enabled:
        try:
            balance = await agent.get_balance()
            account_status = "connected"
        except Exception:
            account_status = "unavailable"

    research_model = os.getenv("RESEARCH_MODEL", "meta-llama/Llama-3.3-70B-Instruct").split("/")[-1]
    trading_model = os.getenv("TRADING_MODEL", "meta-llama/Llama-3.3-70B-Instruct").split("/")[-1]
    return {
        "mode": "analysis_only",
        "execution_enabled": False,
        "exchange_status": "public_market_data_only",
        "account_status": account_status,
        "balance": balance,
        "history": [serialize_document(item) for item in history],
        "pnl_24h": None,
        "active_strategy": f"Market Analysis ({trading_model} + {research_model})",
        "data_source": "kraken_spot_rest",
    }


@router.get("/ledger")
async def get_ledger():
    db = await get_database()
    history = await db.trading_ledger.find().sort("timestamp", -1).limit(100).to_list(length=100)
    return [serialize_document(item) for item in history]


@router.get("/audit")
async def get_audit_logs():
    db = await get_database()
    logs = await db.audit_logs.find().sort("timestamp", -1).limit(100).to_list(length=100)
    return [serialize_document(item) for item in logs]


@router.get("/boardroom")
async def get_boardroom_history():
    db = await get_database()
    history = await db.boardroom_history.find().sort("timestamp", -1).limit(50).to_list(length=50)
    return [serialize_document(item) for item in history]


async def scan_and_analyze() -> Dict[str, Any]:
    # Database availability is a prerequisite for an auditable scan.
    db = await get_database()
    k_agent = get_kraken_agent()
    trading_pair = os.getenv("TRADING_PAIR", "BTC/USD")

    ticker, candles = await __import__("asyncio").gather(
        k_agent.get_ticker(trading_pair),
        k_agent.get_ohlc(trading_pair),
    )

    baseline = whipsaw_protection.evaluate_signal_quality(candles, [], "HOLD")
    decision = await boardroom.deliberate(ticker, candles, trading_pair, baseline)
    proposed_action = str(decision.get("action", "HOLD")).upper()

    final_report = whipsaw_protection.evaluate_signal_quality(candles, [], proposed_action)
    if final_report.get("action_recommendation") == "FORCE_HOLD" and proposed_action != "HOLD":
        decision["action"] = "HOLD"
        decision["reasoning"] = (
            f"[WHIPSAW PROTECTION] Proposed {proposed_action} changed to HOLD. "
            f"{final_report.get('reason', 'Signal quality threshold not met.')}"
        )

    timestamp = utc_now()
    deliberation = {
        **decision,
        "timestamp": timestamp,
        "pair": trading_pair,
        "signal_quality": final_report.get("signal_quality_index"),
        "whipsaw_risk": final_report.get("whipsaw_risk"),
        "market_data_source": "kraken",
        "execution_status": "disabled",
    }
    audit = {
        "timestamp": timestamp,
        "agent": "Boardroom",
        "action": f"Proposed {str(decision.get('action', 'HOLD')).upper()}",
        "reasoning": str(decision.get("reasoning", "")),
        "status": "analysis_recorded",
        "execution_enabled": False,
    }

    # If either durable write fails, the scan fails. It must not report success
    # with an incomplete audit trail.
    await db.boardroom_history.insert_one(dict(deliberation))
    await db.audit_logs.insert_one(dict(audit))

    return {
        "pair": trading_pair,
        "ticker": ticker,
        "decision": decision,
        "trade": None,
        "execution_status": "disabled",
        "signal_quality_report": final_report,
    }


@router.post("/scan")
async def scan_and_analyze_route():
    try:
        return await scan_and_analyze()
    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose provider errors or fall back to fabricated prices.
        raise HTTPException(
            status_code=503,
            detail="Market analysis is temporarily unavailable. No order was submitted.",
        ) from exc


@router.post("/manual")
async def manual_trade(request: Request):
    # Manual execution remains disabled until authentication, a deterministic
    # risk gate, idempotency, and exchange-confirmed order lifecycle are ready.
    raise HTTPException(
        status_code=423,
        detail="Trade execution is disabled during the safety and exchange-adapter build.",
    )
