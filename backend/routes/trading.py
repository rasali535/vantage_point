from datetime import datetime, timezone
import os
from typing import Any, Dict, Literal
import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from agents.kraken import KrakenAgent
from agents.orchestrator import trading_orchestrator
from agents.contracts import PortfolioRiskSnapshot, TradeAction
from agents.whipsaw_protection import whipsaw_protection
from database import get_database
from risk.engine import RiskPolicy, DeterministicRiskEngine
from paper_trading.engine import (
    PaperTradeError, account_summary, initial_account, simulate_order,
)

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

    research_model = os.getenv("RESEARCH_MODEL", "muse-spark-1.3").split("/")[-1]
    trading_model = os.getenv("TRADING_MODEL", "muse-spark-1.3").split("/")[-1]
    risk_policy_configured = RiskPolicy.from_env() is not None
    return {
        "mode": "analysis_only",
        "execution_enabled": False,
        "risk_policy_status": "configured" if risk_policy_configured else "not_configured",
        "exchange_status": "public_market_data_only",
        "account_status": account_status,
        "balance": balance,
        "history": [serialize_document(item) for item in history],
        "pnl_24h": None,
        "active_strategy": f"Market Analysis ({trading_model} + {research_model})",
        "data_source": "kraken_spot_rest",
        "agents": [
            {"id": "market_intelligence", "status": "ready", "provider": "meta"},
            {"id": "technical_analyst", "status": "ready", "provider": "deterministic"},
            {"id": "strategy", "status": "ready", "provider": "meta"},
            {"id": "risk_manager", "status": "advisory_only", "provider": "meta"},
            {"id": "execution", "status": "disabled", "provider": "deterministic_risk_gate"},
            {"id": "performance", "status": "read_only", "provider": "mongodb_ledger"},
        ],
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

    import asyncio
    ticker, candles = await asyncio.gather(
        k_agent.get_ticker(trading_pair),
        k_agent.get_ohlc(trading_pair),
    )

    portfolio = PortfolioRiskSnapshot()
    closed_trades = await db.trading_ledger.find({
        "status": "closed", "exchange_confirmed": True
    }).sort("timestamp", -1).limit(100).to_list(length=100)

    cycle = await trading_orchestrator.run(
        pair=trading_pair,
        ticker=ticker,
        candles=candles,
        portfolio=portfolio,
        closed_trades=closed_trades,
    )

    final_report = whipsaw_protection.evaluate_signal_quality(
        candles, closed_trades, cycle.strategy.action.value
    )
    if final_report.get("action_recommendation") in {"FORCE_HOLD", "ADVISE_HOLD"} and cycle.strategy.action != TradeAction.HOLD:
        cycle.strategy.action = TradeAction.HOLD
        cycle.strategy.rationale = (
            f"[DETERMINISTIC WHIPSAW FILTER] Changed proposal to HOLD. "
            f"{final_report.get('reason', 'Signal quality threshold not met.')}"
        )
        cycle.execution_assessment.status = "hold"
        cycle.execution_assessment.reasons.append("Deterministic whipsaw filter requires HOLD.")

    timestamp = utc_now()
    cycle_payload = cycle.model_dump(mode="json")
    deliberation = {
        **cycle_payload,
        "timestamp": timestamp,
        "market_data_source": "kraken_spot_rest",
        "execution_status": "disabled",
    }
    audit = {
        "timestamp": timestamp,
        "agent": "six_agent_orchestrator",
        "agents": [
            "market_intelligence", "technical_analyst", "strategy",
            "risk_manager", "execution", "performance",
        ],
        "action": f"Proposed {cycle.strategy.action.value}",
        "reasoning": cycle.strategy.rationale,
        "status": "analysis_recorded",
        "execution_enabled": False,
    }

    # If either durable write fails, the scan fails. No incomplete cycle is
    # reported as successful and no order submission is attempted.
    await db.boardroom_history.insert_one(dict(deliberation))
    await db.audit_logs.insert_one(dict(audit))

    return {
        "pair": trading_pair,
        "ticker": ticker,
        "decision": {
            "action": cycle.strategy.action.value,
            "reasoning": cycle.strategy.rationale,
            "confidence": cycle.strategy.confidence,
            "risk_score": None,
            "agents": cycle_payload,
        },
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


class PaperOrderRequest(BaseModel):
    pair: str = Field(min_length=3, max_length=20)
    side: Literal["BUY", "SELL"]
    quantity: str = Field(min_length=1, max_length=40)
    idempotency_key: str = Field(min_length=1, max_length=128)
    stop_loss_price: str | None = Field(default=None, max_length=40)


def _require_paper_access(token: str | None) -> None:
    if os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=423, detail="Paper trading is disabled by the operator.")
    expected = os.getenv("PAPER_API_TOKEN")
    if not expected or not token or not hmac.compare_digest(expected, token):
        raise HTTPException(status_code=401, detail="Valid paper-trading access token required.")
    if not os.getenv("PAPER_INITIAL_BALANCE_USD"):
        raise HTTPException(status_code=503, detail="Configure PAPER_INITIAL_BALANCE_USD before initializing the paper account.")


async def _get_or_create_paper_account(db):
    account = await db.paper_accounts.find_one({"_id": "default"})
    if account:
        return account
    try:
        seed = initial_account(os.environ["PAPER_INITIAL_BALANCE_USD"])
        await db.paper_accounts.insert_one(seed)
    except DuplicateKeyError:
        pass
    except (KeyError, PaperTradeError) as exc:
        raise HTTPException(status_code=503, detail="Paper account configuration is invalid or incomplete.") from exc
    return await db.paper_accounts.find_one({"_id": "default"})


@router.get("/paper/account")
async def get_paper_account(x_paper_token: str | None = Header(default=None)):
    _require_paper_access(x_paper_token)
    db = await get_database()
    account = await _get_or_create_paper_account(db)
    prices = {}
    for position in account.get("positions", {}).keys():
        ticker = await get_kraken_agent().get_ticker(position)
        prices[position] = ticker["last"]
    return account_summary(account, prices)


@router.get("/paper/orders")
async def get_paper_orders(x_paper_token: str | None = Header(default=None)):
    _require_paper_access(x_paper_token)
    db = await get_database()
    account = await _get_or_create_paper_account(db)
    return list(reversed(account.get("orders", [])[-100:]))


@router.post("/paper/orders")
async def submit_paper_order(
    payload: PaperOrderRequest,
    x_paper_token: str | None = Header(default=None),
):
    _require_paper_access(x_paper_token)
    db = await get_database()
    try:
        ticker = await get_kraken_agent().get_ticker(payload.pair)
        reference_price = ticker["last"]
        for _attempt in range(5):
            account = await _get_or_create_paper_account(db)
            updated, fill = simulate_order(
                account,
                pair=payload.pair,
                side=payload.side,
                quantity=payload.quantity,
                reference_price=reference_price,
                idempotency_key=payload.idempotency_key,
                stop_loss_price=payload.stop_loss_price,
                risk_engine=DeterministicRiskEngine(),
            )
            if fill.get("duplicate"):
                return {"fill": fill, "account": account_summary(account), "execution_mode": "paper"}
            update_fields = {key: value for key, value in updated.items() if key != "_id"}
            saved = await db.paper_accounts.find_one_and_update(
                {"_id": "default", "version": account.get("version", 0)},
                {"$set": update_fields},
                return_document=ReturnDocument.AFTER,
            )
            if saved:
                await db.audit_logs.insert_one({
                    "timestamp": utc_now(),
                    "agent": "paper_execution",
                    "action": f"Simulated {payload.side} {payload.pair}",
                    "status": "paper_fill_recorded",
                    "execution_enabled": False,
                    "exchange_order_submitted": False,
                    "idempotency_key": payload.idempotency_key,
                })
                return {
                    "fill": fill,
                    "account": account_summary(saved, {payload.pair: reference_price}),
                    "execution_mode": "paper",
                    "exchange_order_submitted": False,
                }
        raise HTTPException(status_code=409, detail="Paper account changed concurrently; retry with the same idempotency key.")
    except HTTPException:
        raise
    except PaperTradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Paper trading is temporarily unavailable. No live order was submitted.") from exc
