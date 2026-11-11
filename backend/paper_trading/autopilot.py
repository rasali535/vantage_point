"""Autonomous paper-only trading supervisor.

This worker can create simulated fills in MongoDB. It has no broker order
adapter and never calls a private exchange endpoint.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_DOWN

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from agents.contracts import PortfolioRiskSnapshot, TradeAction
from agents.kraken import KrakenAgent
from agents.orchestrator import TradingOrchestrator
from agents.whipsaw_protection import whipsaw_protection
from database import get_database
from paper_trading.engine import (
    PaperTradeError,
    account_equity,
    evaluate_protective_triggers,
    initial_account,
    simulate_order,
)
from risk.engine import DeterministicRiskEngine, RiskPolicy

logger = logging.getLogger(__name__)
D = Decimal
QTY_STEP = D("0.00000001")
_worker_task: asyncio.Task | None = None
_worker_owner = uuid.uuid4().hex
_market = KrakenAgent()
_orchestrator = TradingOrchestrator()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enabled_by_operator() -> bool:
    return os.getenv("PAPER_AUTOTRADING_ALLOWED", "true").lower() == "true"


def configured_pairs() -> list[str]:
    raw = os.getenv("PAPER_AUTOTRADE_PAIRS", os.getenv("TRADING_PAIR", "BTC/USD"))
    pairs = list(dict.fromkeys(item.strip().upper() for item in raw.split(",") if item.strip()))
    if (
        not pairs or len(pairs) > 20
        or any("/" not in pair or pair.split("/")[-1] != "USD" for pair in pairs)
    ):
        raise PaperTradeError("The current Kraken spot autopilot accepts 1–20 USD-quoted crypto pairs only.")
    return pairs


def calculate_spot_quantity(
    equity: Decimal,
    cash: Decimal,
    entry_estimate: Decimal,
    stop_price: Decimal,
    risk_pct: Decimal,
    fee_rate: Decimal,
) -> Decimal:
    """Size a fully-collateralized spot BUY to the configured stop-risk budget."""
    if min(equity, cash, entry_estimate, stop_price, risk_pct) <= 0 or stop_price >= entry_estimate:
        raise PaperTradeError("Cannot size an entry from invalid equity, cash, entry or stop values.")
    risk_budget = equity * risk_pct / D("100")
    risk_quantity = risk_budget / (entry_estimate - stop_price)
    cash_quantity = cash / (entry_estimate * (D("1") + fee_rate))
    return min(risk_quantity, cash_quantity).quantize(QTY_STEP, rounding=ROUND_DOWN)


async def _get_account(db) -> dict:
    account = await db.paper_accounts.find_one({"_id": "default"})
    if account:
        return account
    seed = initial_account(os.environ["PAPER_INITIAL_BALANCE_USD"])
    try:
        await db.paper_accounts.insert_one(seed)
    except DuplicateKeyError:
        pass
    account = await db.paper_accounts.find_one({"_id": "default"})
    if not account:
        raise PaperTradeError("Paper account could not be initialized.")
    return account


async def _save_account(db, before: dict, after: dict) -> dict:
    fields = {key: value for key, value in after.items() if key != "_id"}
    saved = await db.paper_accounts.find_one_and_update(
        {"_id": "default", "version": before.get("version", 0)},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )
    if not saved:
        raise PaperTradeError("Paper account changed concurrently; retry the next autonomous cycle.")
    return saved


async def _record_event(db, event: dict) -> None:
    record = {
        "_id": event.get("idempotency_key") or uuid.uuid4().hex,
        "timestamp": event.get("timestamp", _utcnow().isoformat()),
        "execution_mode": "paper",
        "exchange_order_submitted": False,
        **event,
    }
    try:
        await db.paper_autopilot_events.insert_one(record)
    except DuplicateKeyError:
        return


async def _acquire_worker_lease(db) -> bool:
    now = _utcnow()
    expires = now + timedelta(seconds=600)
    try:
        await db.paper_autopilot_worker.insert_one({
            "_id": "singleton",
            "owner": _worker_owner,
            "expires_at": expires,
            "heartbeat_at": now,
        })
        return True
    except DuplicateKeyError:
        pass
    lease = await db.paper_autopilot_worker.find_one_and_update(
        {
            "_id": "singleton",
            "$or": [
                {"expires_at": {"$lte": now}},
                {"owner": _worker_owner},
            ],
        },
        {"$set": {"owner": _worker_owner, "expires_at": expires, "heartbeat_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    return bool(lease and lease.get("owner") == _worker_owner)


async def _release_worker_lease(db) -> None:
    await db.paper_autopilot_worker.delete_one({"_id": "singleton", "owner": _worker_owner})


async def _mark_and_protect_positions(db, account: dict) -> tuple[dict, dict[str, Decimal], list[dict]]:
    original = account
    working = dict(account)
    prices: dict[str, Decimal] = {}
    for pair in account.get("positions", {}).keys():
        ticker = await _market.get_ticker(pair)
        prices[pair] = D(str(ticker["last"]))

    equity = account_equity(account, prices)
    peak = max(D(str(account.get("peak_equity", equity))), equity)
    today = _utcnow().date().isoformat()
    day_start = D(str(account.get("day_start_equity", account.get("initial_equity", equity))))
    day_date = account.get("day_start_date")
    if day_date != today:
        day_start, day_date = equity, today

    working["peak_equity"] = str(peak)
    working["day_start_equity"] = str(day_start)
    working["day_start_date"] = day_date

    updated, triggered = evaluate_protective_triggers(working, prices)
    metrics_changed = any(
        updated.get(key) != original.get(key)
        for key in ("peak_equity", "day_start_equity", "day_start_date")
    )
    if triggered or metrics_changed:
        # Protective evaluation increments version when it creates fills.
        if not triggered:
            updated["version"] = int(original.get("version", 0)) + 1
        saved = await _save_account(db, original, updated)
        for fill in triggered:
            await _record_event(db, {
                **fill,
                "event_type": "protective_exit",
                "triggered_by": fill.get("triggered_by"),
            })
        return saved, prices, triggered

    return account, prices, triggered


def _portfolio_snapshot(account: dict, prices: dict[str, Decimal]) -> PortfolioRiskSnapshot:
    equity = account_equity(account, prices)
    peak = D(str(account.get("peak_equity", equity)))
    day_start = D(str(account.get("day_start_equity", account.get("initial_equity", equity))))
    daily_loss = max(D("0"), (day_start - equity) / day_start * D("100")) if day_start > 0 else D("0")
    drawdown = max(D("0"), (peak - equity) / peak * D("100")) if peak > 0 else D("0")
    open_count = sum(1 for item in account.get("positions", {}).values() if D(str(item["quantity"])) > 0)
    return PortfolioRiskSnapshot(
        equity=equity,
        daily_loss_pct=daily_loss,
        drawdown_pct=drawdown,
        open_positions=open_count,
        leverage=D("1"),
    )


async def _execute_signal(db, account: dict, pair: str, ticker: dict, candles: list, portfolio: PortfolioRiskSnapshot, portfolio_prices: dict[str, Decimal]) -> dict:
    cycle = await _orchestrator.run(
        pair=pair,
        ticker=ticker,
        candles=candles,
        portfolio=portfolio,
        closed_trades=account.get("orders", []),
    )
    action = cycle.strategy.action
    confidence_floor = D(os.getenv("PAPER_AUTOTRADING_MIN_CONFIDENCE", "0.70"))
    if not D("0.5") <= confidence_floor <= D("1"):
        return {"pair": pair, "decision": "HOLD", "reason": "Autonomous confidence threshold is outside the safe 0.5–1.0 range."}
    confidence = D(str(cycle.strategy.confidence))
    technical_signal = cycle.technical_analysis.signal
    signal_report = whipsaw_protection.evaluate_signal_quality(candles, [], action.value)
    if signal_report.get("action_recommendation") in {"FORCE_HOLD", "ADVISE_HOLD"}:
        action = TradeAction.HOLD

    current = account.get("positions", {}).get(pair)
    if confidence < confidence_floor or action == TradeAction.HOLD:
        return {"pair": pair, "decision": "HOLD", "reason": "Confidence or signal-quality threshold not met."}

    if action == TradeAction.BUY:
        if technical_signal != TradeAction.BUY or current:
            return {"pair": pair, "decision": "HOLD", "reason": "Technical confirmation missing or position already open."}
        if not cycle.technical_analysis.atr or cycle.technical_analysis.atr <= 0:
            return {"pair": pair, "decision": "HOLD", "reason": "ATR unavailable; safe stop distance cannot be calculated."}

        price = D(str(ticker["last"]))
        from paper_trading.engine import simulation_settings
        fee_rate, slippage_bps = simulation_settings()
        slippage = slippage_bps / D("10000")
        entry_estimate = price * (D("1") + slippage)
        stop_distance = max(D(str(cycle.technical_analysis.atr)) * D("1.5"), entry_estimate * D("0.001"))
        stop = entry_estimate - stop_distance
        target = entry_estimate + stop_distance * D("2")
        policy = RiskPolicy.from_env()
        if policy is None:
            return {"pair": pair, "decision": "REJECTED", "reason": "Risk policy is missing or invalid."}
        quantity = calculate_spot_quantity(
            portfolio.equity,
            D(str(account["cash"])),
            entry_estimate,
            stop,
            policy.max_trade_risk_pct,
            fee_rate,
        )
        if quantity <= 0:
            return {"pair": pair, "decision": "HOLD", "reason": "Risk-sized quantity is below supported precision."}

        updated, fill = simulate_order(
            account,
            pair=pair,
            side="BUY",
            quantity=quantity,
            reference_price=price,
            idempotency_key=f"autopilot:entry:{pair}:{uuid.uuid4().hex}",
            stop_loss_price=stop,
            take_profit_price=target,
            risk_engine=DeterministicRiskEngine(policy),
            portfolio_prices={**portfolio_prices, pair: D(str(ticker["last"]))},
        )
        saved = await _save_account(db, account, updated)
        await _record_event(db, {
            **fill,
            "event_type": "autonomous_entry",
            "strategy_confidence": str(confidence),
            "strategy_rationale": cycle.strategy.rationale[:1000],
            "stop_loss": str(stop),
            "take_profit": str(target),
        })
        return {"pair": pair, "decision": "BUY", "fill": fill, "account_version": saved.get("version")}

    if action == TradeAction.SELL and current:
        if technical_signal != TradeAction.SELL:
            return {"pair": pair, "decision": "HOLD", "reason": "Technical exit confirmation missing."}
        quantity = D(str(current["quantity"]))
        price = D(str(ticker["last"]))
        updated, fill = simulate_order(
            account,
            pair=pair,
            side="SELL",
            quantity=quantity,
            reference_price=price,
            idempotency_key=f"autopilot:signal-exit:{pair}:{current.get('opened_at', 'position')}",
        )
        saved = await _save_account(db, account, updated)
        await _record_event(db, {
            **fill,
            "event_type": "autonomous_signal_exit",
            "strategy_confidence": str(confidence),
            "strategy_rationale": cycle.strategy.rationale[:1000],
        })
        return {"pair": pair, "decision": "SELL", "fill": fill, "account_version": saved.get("version")}

    return {"pair": pair, "decision": "HOLD", "reason": "No compatible open position for this signal."}


async def run_autopilot_cycle(db=None) -> dict:
    """Run one autonomous paper cycle; caller must hold the worker lease."""
    if os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true":
        return {"status": "disabled", "reason": "Paper trading is disabled."}
    if not os.getenv("PAPER_API_TOKEN") or not os.getenv("PAPER_INITIAL_BALANCE_USD"):
        return {"status": "disabled", "reason": "Paper account configuration is incomplete."}
    if not _enabled_by_operator():
        return {"status": "disabled", "reason": "PAPER_AUTOTRADING_ALLOWED is false."}

    db = db or await get_database()
    state = await db.paper_runtime.find_one({"_id": "autopilot"})
    if not state or state.get("enabled") is not True:
        return {"status": "stopped"}

    account = await _get_account(db)
    account, held_prices, protective_exits = await _mark_and_protect_positions(db, account)
    portfolio = _portfolio_snapshot(account, held_prices)
    policy = RiskPolicy.from_env()
    if policy is None:
        return {"status": "blocked", "reason": "Risk policy is missing or invalid.", "protective_exits": protective_exits}

    # A loss-limit breach blocks new entries, but does not disable position protection.
    portfolio_gate = DeterministicRiskEngine(policy).evaluate_portfolio_state(
        daily_loss_pct=portfolio.daily_loss_pct,
        drawdown_pct=portfolio.drawdown_pct,
        open_positions=portfolio.open_positions,
        leverage=portfolio.leverage,
    )
    results = []
    if portfolio_gate.get("approved"):
        for pair in configured_pairs():
            try:
                ticker, candles = await asyncio.gather(
                    _market.get_ticker(pair),
                    _market.get_ohlc(pair, interval=int(os.getenv("PAPER_AUTOTRADING_CANDLE_INTERVAL", "60"))),
                )
                result = await _execute_signal(db, account, pair, ticker, candles, portfolio, held_prices)
                results.append(result)
                # Reload after a fill so subsequent instruments use the same
                # shared portfolio equity, cash and position budget.
                account = await _get_account(db)
                account, held_prices, _ = await _mark_and_protect_positions(db, account)
                portfolio = _portfolio_snapshot(account, held_prices)
                portfolio_gate = DeterministicRiskEngine(policy).evaluate_portfolio_state(
                    daily_loss_pct=portfolio.daily_loss_pct,
                    drawdown_pct=portfolio.drawdown_pct,
                    open_positions=portfolio.open_positions,
                    leverage=portfolio.leverage,
                )
                if not portfolio_gate.get("approved"):
                    break
            except Exception as exc:
                logger.exception("paper_autopilot_pair_failed pair=%s error_type=%s", pair, type(exc).__name__)
                results.append({"pair": pair, "decision": "SKIPPED", "reason": "Provider, analysis or paper execution failed closed."})

    summary = {
        "status": "completed",
        "timestamp": _utcnow().isoformat(),
        "pairs_checked": len(results),
        "results": results,
        "protective_exits": protective_exits,
        "portfolio_gate": portfolio_gate,
        "execution_mode": "paper",
        "exchange_order_submitted": False,
    }
    await db.paper_autopilot_runs.insert_one(dict(summary))
    return summary


async def _worker_loop() -> None:
    monitor_interval = max(10, min(60, int(os.getenv("PAPER_AUTOTRADING_MONITOR_SECONDS", "20"))))
    scan_interval = max(60, min(1800, int(os.getenv("PAPER_AUTOTRADING_SCAN_SECONDS", "300"))))
    last_scan = 0.0
    while True:
        try:
            db = await get_database()
            state = await db.paper_runtime.find_one({"_id": "autopilot"})
            if os.getenv("PAPER_TRADING_ENABLED", "false").lower() == "true" and os.getenv("PAPER_INITIAL_BALANCE_USD"):
                if await _acquire_worker_lease(db):
                    try:
                        if state and state.get("enabled") is True and _enabled_by_operator():
                            now = asyncio.get_running_loop().time()
                            if now - last_scan >= scan_interval:
                                await run_autopilot_cycle(db)
                                last_scan = now
                            else:
                                account = await db.paper_accounts.find_one({"_id": "default"})
                                if account and account.get("positions"):
                                    await _mark_and_protect_positions(db, account)
                        else:
                            # Stopping new entries does not abandon protective
                            # exits for positions already open in the virtual account.
                            account = await db.paper_accounts.find_one({"_id": "default"})
                            if account and account.get("positions"):
                                await _mark_and_protect_positions(db, account)
                    finally:
                        await _release_worker_lease(db)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("paper_autopilot_worker_error error_type=%s", type(exc).__name__)
        await asyncio.sleep(monitor_interval)


def start_worker() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop(), name="paper-autopilot-worker")


async def stop_worker() -> None:
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None


async def set_autopilot_enabled(db, enabled: bool) -> dict:
    if enabled and (not _enabled_by_operator() or os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true"):
        raise PaperTradeError("Autonomous paper trading is not permitted by server configuration.")
    record = {
        "_id": "autopilot",
        "enabled": enabled,
        "updated_at": _utcnow().isoformat(),
        "mode": "paper",
        "exchange_order_submitted": False,
    }
    await db.paper_runtime.update_one({"_id": "autopilot"}, {"$set": record}, upsert=True)
    return record


async def autopilot_status(db) -> dict:
    state = await db.paper_runtime.find_one({"_id": "autopilot"}) or {"enabled": False}
    return {
        "enabled": state.get("enabled") is True,
        "worker_configured": _enabled_by_operator(),
        "paper_trading_enabled": os.getenv("PAPER_TRADING_ENABLED", "false").lower() == "true",
        "monitor_interval_seconds": max(10, min(60, int(os.getenv("PAPER_AUTOTRADING_MONITOR_SECONDS", "20")))),
        "scan_interval_seconds": max(60, min(1800, int(os.getenv("PAPER_AUTOTRADING_SCAN_SECONDS", "300")))),
        "pairs": configured_pairs(),
        "execution_mode": "paper",
        "live_execution_enabled": False,
    }
