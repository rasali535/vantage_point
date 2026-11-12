from datetime import datetime, timezone
import logging
import uuid
import os
from typing import Any, Dict, Literal
import hmac
import hashlib
import socket
import time

import httpx

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from agents.kraken import KrakenAgent
from agents.meta_ai import meta_ai, MetaAIError, meta_http_transport
from agents.orchestrator import trading_orchestrator, AgentStageTimeout
from agents.contracts import PortfolioRiskSnapshot, TradeAction
from agents.whipsaw_protection import whipsaw_protection
from database import get_database
from risk.engine import RiskPolicy, DeterministicRiskEngine
from paper_trading.engine import (
    PaperTradeError, account_summary, initial_account, simulate_order,
    evaluate_protective_triggers,
)
from paper_trading.autopilot import autopilot_status, run_autopilot_once, set_autopilot_enabled

router = APIRouter()
logger = logging.getLogger(__name__)
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
    meta_status = "ready" if meta_ai.api_key else "not_configured"
    meta_risk_status = "advisory_only" if meta_ai.api_key else "not_configured"
    return {
        "mode": "analysis_only",
        "execution_enabled": False,
        "paper_trading_available": os.getenv("PAPER_TRADING_ENABLED", "false").lower() == "true" and bool(os.getenv("PAPER_API_TOKEN")) and bool(os.getenv("PAPER_INITIAL_BALANCE_USD")),
        "live_execution_enabled": False,
        "risk_policy_status": "configured" if risk_policy_configured else "not_configured",
        "exchange_status": "public_market_data_only",
        "account_status": account_status,
        "balance": balance,
        "history": [serialize_document(item) for item in history],
        "pnl_24h": None,
        "active_strategy": f"Market Analysis ({trading_model} + {research_model})",
        "data_source": "kraken_spot_rest",
        "agents": [
            {"id": "market_intelligence", "status": meta_status, "provider": "meta"},
            {"id": "technical_analyst", "status": "ready", "provider": "deterministic"},
            {"id": "strategy", "status": meta_status, "provider": "meta"},
            {"id": "risk_manager", "status": meta_risk_status, "provider": "meta"},
            {"id": "execution", "status": "disabled", "provider": "deterministic_risk_gate"},
            {"id": "performance", "status": "read_only", "provider": "mongodb_ledger"},
        ],
    }


@router.get("/meta/readiness")
async def get_meta_readiness():
    # No secrets are exposed; the key appears only as a fingerprint.
    return await meta_ai.check_readiness()


@router.get("/meta/debug/upstream")
async def debug_meta_upstream():
    """Probe the Meta API from inside this process and report raw results.

    Debugging aid for path-dependent upstream failures. Reports statuses,
    response prefixes, DNS resolution, and header shape only. The API key
    itself is never included; it appears solely as a fingerprint.
    """
    meta_ai._refresh_credentials()
    fingerprint = (
        hashlib.sha256(meta_ai.api_key.encode("utf-8")).hexdigest()[:16]
        if meta_ai.api_key
        else "missing"
    )
    report: Dict[str, Any] = {
        "key_configured": bool(meta_ai.api_key),
        "key_fingerprint": fingerprint,
        "base_url": meta_ai.base_url,
    }
    try:
        addr_infos = socket.getaddrinfo("api.meta.ai", 443, type=socket.SOCK_STREAM)
        seen = set()
        dns: list = []
        for family, _, _, _, sockaddr in addr_infos:
            entry = f"{family!s}:{sockaddr[0]}"
            if entry not in seen:
                seen.add(entry)
                dns.append(entry)
        report["dns_api_meta_ai"] = dns
    except Exception as exc:
        report["dns_api_meta_ai"] = {"error": type(exc).__name__}

    headers = meta_ai._headers()
    report["request_headers"] = {
        name: ("<redacted-present>" if name.lower() == "authorization" else value)
        for name, value in headers.items()
    }
    report["auth_header_length"] = len(headers.get("Authorization", ""))

    proxy_vars = []
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        if os.getenv(var) or os.getenv(var.lower()):
            proxy_vars.append(var)
    report["proxy_env_present"] = proxy_vars or "none"

    tcp_results: Any = []
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(
            "api.meta.ai", 443, type=socket.SOCK_STREAM
        ):
            ip = sockaddr[0]
            started = time.monotonic()
            try:
                sock = socket.create_connection((ip, 443), timeout=4)
                elapsed_ms = round((time.monotonic() - started) * 1000)
                sock.close()
                tcp_results.append(
                    {"ip": ip, "family": f"{family!s}", "connected": True, "elapsed_ms": elapsed_ms}
                )
                break
            except Exception as exc:
                tcp_results.append(
                    {"ip": ip, "family": f"{family!s}", "connected": False, "error": type(exc).__name__}
                )
    except Exception as exc:
        tcp_results = {"error": type(exc).__name__}
    report["tcp_connect_probe"] = tcp_results

    chat_payload = {
        "model": "muse-spark-1.3",
        "messages": [{"role": "user", "content": "Reply with the word OK."}],
        "max_completion_tokens": 5,
    }
    report["chat_payload_sent"] = chat_payload

    async def _probe(method: str, path: str, payload: Any = None) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), transport=meta_http_transport()) as client:
                if method == "GET":
                    response = await client.get(f"{meta_ai.base_url}{path}", headers=headers)
                else:
                    response = await client.post(
                        f"{meta_ai.base_url}{path}", headers=headers, json=payload
                    )
            return {
                "http_status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "body_prefix": response.text[:600],
            }
        except Exception as exc:
            return {"error": type(exc).__name__, "detail": str(exc)[:200]}

    report["get_models"] = await _probe("GET", "/models")
    report["post_chat_completions"] = await _probe("POST", "/chat/completions", chat_payload)
    return report


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


async def scan_and_analyze(pair: str | None = None) -> Dict[str, Any]:
    # Database availability is a prerequisite for an auditable scan.
    db = await get_database()
    k_agent = get_kraken_agent()
    trading_pair = (pair or os.getenv("TRADING_PAIR", "BTC/USD")).strip().upper()

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
    if final_report.get("action_recommendation") == "FORCE_HOLD" and cycle.strategy.action != TradeAction.HOLD:
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

class ScanRequest(BaseModel):
    """Optional scan overrides. An absent body preserves the legacy contract."""

    pair: str | None = Field(default=None, min_length=3, max_length=20)

    @field_validator("pair")
    @classmethod
    def normalize_pair(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        base, separator, quote = cleaned.partition("/")
        if not separator or not base.isalnum() or not quote.isalnum():
            raise ValueError("pair must look like BASE/QUOTE, e.g. ETH/USD")
        return f"{base}/{quote}"


@router.post("/scan")
async def scan_and_analyze_route(payload: ScanRequest | None = None):
    request_id = uuid.uuid4().hex
    started = datetime.now(timezone.utc)
    try:
        result = await scan_and_analyze(pair=payload.pair if payload else None)
        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        logger.info("trading_scan_completed request_id=%s elapsed_ms=%d", request_id, elapsed_ms)
        return result
    except HTTPException:
        raise
    except MetaAIError as exc:
        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        logger.warning(
            "trading_scan_meta_provider_failed request_id=%s elapsed_ms=%d code=%s error=%s",
            request_id, elapsed_ms, exc.error_code, exc.message,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"Market analysis unavailable: {exc.message} No order was submitted.",
                "error_code": exc.error_code or "meta_provider_error",
                "request_id": request_id,
            },
        ) from exc
    except Exception as exc:
        # Keep provider details server-side; never fall back to fabricated data.
        if isinstance(exc, AgentStageTimeout):
            elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000)
            logger.warning(
                "trading_scan_stage_timeout request_id=%s elapsed_ms=%d stage=%s",
                request_id, elapsed_ms, exc.stage,
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "message": (
                        f"Market analysis timed out during {exc.stage} "
                        f"({exc.timeout_seconds:.0f}s budget). No order was submitted."
                    ),
                    "error_code": "agent_stage_timeout",
                    "request_id": request_id,
                },
            ) from exc
        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        logger.exception(
            "trading_scan_failed request_id=%s elapsed_ms=%d error_type=%s",
            request_id, elapsed_ms, type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Market analysis is temporarily unavailable. No order was submitted.",
                "request_id": request_id,
            },
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
    take_profit_price: str | None = Field(default=None, max_length=40)


def _require_paper_access(token: str | None) -> None:
    if os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=423, detail="Paper trading is disabled by the operator.")
    expected = os.getenv("PAPER_API_TOKEN")
    if not expected or not token or not hmac.compare_digest(expected, token):
        raise HTTPException(status_code=401, detail="Valid paper-trading access token required.")
    if not os.getenv("PAPER_INITIAL_BALANCE_USD"):
        raise HTTPException(status_code=503, detail="Configure PAPER_INITIAL_BALANCE_USD before initializing the paper account.")


async def _record_paper_audit(db, fill: dict) -> None:
    try:
        await db.audit_logs.insert_one({
            "_id": f"paper:{fill['idempotency_key']}",
            "timestamp": fill["timestamp"],
            "agent": "paper_execution",
            "action": f"Simulated {fill['side']} {fill['pair']} ({fill.get('quantity')} @ {fill.get('fill_price')})",
            "reasoning": f"Paper simulation fill recorded for {fill['pair']}. Live order execution remains disabled.",
            "status": "paper_fill_recorded",
            "execution_enabled": False,
            "exchange_order_submitted": False,
            "idempotency_key": fill["idempotency_key"],
        })
    except DuplicateKeyError:
        pass
    ledger_col = getattr(db, "trading_ledger", None)
    if ledger_col is not None:
        try:
            await ledger_col.insert_one({
                "_id": f"paper_ledger:{fill['idempotency_key']}",
                "id": fill["idempotency_key"],
                "order_id": fill["idempotency_key"],
                "symbol": fill["pair"],
                "pair": fill["pair"],
                "side": str(fill["side"]).lower(),
                "volume": fill.get("quantity"),
                "price": fill.get("fill_price"),
                "status": "paper_filled",
                "execution_mode": "paper",
                "exchange_confirmed": False,
                "exchange_order_submitted": False,
                "realized_pnl_usd": fill.get("realized_pnl_usd"),
                "timestamp": fill["timestamp"],
                "time": fill["timestamp"],
            })
        except Exception:
            pass


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
    try:
        for position in account.get("positions", {}).keys():
            ticker = await get_kraken_agent().get_ticker(position)
            prices[position] = ticker["last"]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Paper account valuation is temporarily unavailable.") from exc
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
        for _attempt in range(5):
            account = await _get_or_create_paper_account(db)
            previous = next(
                (item for item in account.get("orders", []) if item.get("idempotency_key") == payload.idempotency_key),
                None,
            )
            if previous:
                await _record_paper_audit(db, previous)
                return {
                    "fill": {**previous, "duplicate": True},
                    "account": account_summary(account),
                    "execution_mode": "paper",
                    "exchange_order_submitted": False,
                }

            ticker = await get_kraken_agent().get_ticker(payload.pair)
            reference_price = ticker["last"]
            portfolio_prices = {}
            for held_pair in account.get("positions", {}).keys():
                held_ticker = await get_kraken_agent().get_ticker(held_pair)
                portfolio_prices[held_pair] = held_ticker["last"]

            stop_loss_price = payload.stop_loss_price
            take_profit_price = payload.take_profit_price
            if payload.side == "BUY" and (stop_loss_price is None or not str(stop_loss_price).strip()):
                from decimal import Decimal
                ref_dec = Decimal(str(reference_price))
                stop_loss_price = str((ref_dec * Decimal("0.992")).quantize(Decimal("0.00001")))
                if take_profit_price is None or not str(take_profit_price).strip():
                    take_profit_price = str((ref_dec * Decimal("1.016")).quantize(Decimal("0.00001")))

            updated, fill = simulate_order(
                account,
                pair=payload.pair,
                side=payload.side,
                quantity=payload.quantity,
                reference_price=reference_price,
                idempotency_key=payload.idempotency_key,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                risk_engine=DeterministicRiskEngine(),
                portfolio_prices=portfolio_prices,
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
                await _record_paper_audit(db, fill)
                return {
                    "fill": fill,
                    "account": account_summary(saved, {**portfolio_prices, payload.pair: reference_price}),
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


@router.post("/paper/monitor")
async def monitor_paper_positions(x_paper_token: str | None = Header(default=None)):
    """Mark virtual positions and simulate stop-loss/take-profit exits."""
    _require_paper_access(x_paper_token)
    db = await get_database()
    try:
        for _attempt in range(5):
            account = await _get_or_create_paper_account(db)
            prices = {}
            for pair in account.get("positions", {}).keys():
                ticker = await get_kraken_agent().get_ticker(pair)
                prices[pair] = ticker["last"]
            updated, triggered = evaluate_protective_triggers(account, prices)
            if not triggered:
                return {
                    "execution_mode": "paper",
                    "monitored_positions": len(account.get("positions", {})),
                    "triggered_exits": [],
                    "exchange_order_submitted": False,
                }
            fields = {key: value for key, value in updated.items() if key != "_id"}
            saved = await db.paper_accounts.find_one_and_update(
                {"_id": "default", "version": account.get("version", 0)},
                {"$set": fields},
                return_document=ReturnDocument.AFTER,
            )
            if saved:
                for fill in triggered:
                    await _record_paper_audit(db, fill)
                return {
                    "execution_mode": "paper",
                    "triggered_exits": triggered,
                    "account": account_summary(saved, prices),
                    "exchange_order_submitted": False,
                }
        raise HTTPException(status_code=409, detail="Paper account changed concurrently; retry monitoring.")
    except HTTPException:
        raise
    except PaperTradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Paper protective monitoring is temporarily unavailable.") from exc



@router.get("/paper/autopilot")
async def get_paper_autopilot_status(x_paper_token: str | None = Header(default=None)):
    _require_paper_access(x_paper_token)
    db = await get_database()
    try:
        return await autopilot_status(db)
    except PaperTradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/paper/autopilot/start")
async def start_paper_autopilot(x_paper_token: str | None = Header(default=None)):
    import asyncio
    _require_paper_access(x_paper_token)
    db = await get_database()
    try:
        result = await set_autopilot_enabled(db, True)
        asyncio.create_task(run_autopilot_once(db))
        return result
    except PaperTradeError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc


@router.post("/paper/autopilot/run")
async def run_paper_autopilot_now(x_paper_token: str | None = Header(default=None)):
    _require_paper_access(x_paper_token)
    db = await get_database()
    try:
        await set_autopilot_enabled(db, True)
        return await run_autopilot_once(db)
    except PaperTradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/paper/autopilot/stop")
async def stop_paper_autopilot(x_paper_token: str | None = Header(default=None)):
    _require_paper_access(x_paper_token)
    db = await get_database()
    try:
        return await set_autopilot_enabled(db, False)
    except PaperTradeError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc



@router.get("/paper/autopilot/runs")
async def get_paper_autopilot_runs(x_paper_token: str | None = Header(default=None)):
    _require_paper_access(x_paper_token)
    db = await get_database()
    runs = await db.paper_autopilot_runs.find().sort("timestamp", -1).limit(30).to_list(length=30)
    return [serialize_document(item) for item in runs]
