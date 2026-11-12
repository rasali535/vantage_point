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
from agents.technical_analyst import TechnicalAnalystAgent
from agents.whipsaw_protection import whipsaw_protection
from database import get_database
from paper_trading.engine import (
    PaperTradeError,
    account_equity,
    evaluate_protective_triggers,
    initial_account,
    instrument_category,
    is_supported_paper_pair,
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
_technical_precheck = TechnicalAnalystAgent()

DEFAULT_AUTOTRADE_PAIRS = (
    "EUR/USD,GBP/USD,USD/JPY,AUD/USD,USD/CAD,USD/CHF,EUR/GBP,EUR/JPY,"
    "XAU/USD,XAG/USD,XPT/USD,XCU/USD,"
    "SPX500/USD,NAS100/USD,US30/USD,GER40/USD,"
    "BTC/USD,ETH/USD,SOL/USD,XRP/USD"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enabled_by_operator() -> bool:
    return os.getenv("PAPER_AUTOTRADING_ALLOWED", "true").lower() == "true"


def configured_pairs() -> list[str]:
    raw = os.getenv("PAPER_AUTOTRADE_PAIRS", DEFAULT_AUTOTRADE_PAIRS)
    pairs = list(dict.fromkeys(item.strip().upper() for item in raw.split(",") if item.strip()))
    if (
        not pairs or len(pairs) > 25
        or any(not is_supported_paper_pair(pair) for pair in pairs)
    ):
        raise PaperTradeError("The paper autopilot accepts 1–25 Forex or USD-quoted spot pairs only.")
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
    record_id = event.get("idempotency_key") or uuid.uuid4().hex
    timestamp = event.get("timestamp", _utcnow().isoformat())
    record = {
        "_id": record_id,
        "timestamp": timestamp,
        "execution_mode": "paper",
        "exchange_order_submitted": False,
        **event,
    }
    try:
        await db.paper_autopilot_events.insert_one(record)
    except DuplicateKeyError:
        return

    ledger_col = getattr(db, "trading_ledger", None)
    if ledger_col is not None and event.get("pair") and event.get("side"):
        try:
            await ledger_col.insert_one({
                "_id": f"paper_ledger:{record_id}",
                "id": record_id,
                "order_id": record_id,
                "symbol": event["pair"],
                "pair": event["pair"],
                "category": instrument_category(event["pair"]),
                "side": str(event["side"]).lower(),
                "volume": event.get("quantity"),
                "price": event.get("fill_price"),
                "gross_usd": event.get("gross_usd"),
                "fee_usd": event.get("fee_usd"),
                "status": "paper_filled",
                "execution_mode": "paper",
                "exchange_confirmed": False,
                "exchange_order_submitted": False,
                "realized_pnl_usd": event.get("realized_pnl_usd"),
                "timestamp": timestamp,
                "time": timestamp,
            })
        except Exception:
            pass

    boardroom_col = getattr(db, "boardroom_history", None)
    if boardroom_col is not None and event.get("pair") and event.get("side"):
        try:
            await boardroom_col.insert_one({
                "_id": f"paper_boardroom:{record_id}",
                "pair": event["pair"],
                "category": instrument_category(event["pair"]),
                "timestamp": timestamp,
                "strategy": {
                    "action": str(event["side"]).upper(),
                    "confidence": float(event.get("strategy_confidence") or 0.72),
                    "rationale": event.get("strategy_rationale") or f"Autonomous {event['side']} execution on {event['pair']} @ {event.get('fill_price')}.",
                },
                "technical_analysis": event.get("technical_analysis") or {},
                "risk_assessment": {"summary": "Approved by DeterministicRiskEngine"},
                "execution_assessment": {"status": "paper_simulated", "execution_enabled": False},
                "execution_status": "paper_simulated",
            })
        except Exception:
            pass

    audit_col = getattr(db, "audit_logs", None)
    if audit_col is not None and event.get("pair") and event.get("side"):
        try:
            await audit_col.insert_one({
                "_id": f"paper_audit:{record_id}",
                "timestamp": timestamp,
                "agent": "autonomous_paper_supervisor",
                "action": f"Simulated {event['side']} {event['pair']} ({event.get('quantity')} @ {event.get('fill_price')})",
                "reasoning": event.get("strategy_rationale") or f"Protective/autonomous paper execution ({event.get('event_type', 'paper_fill')}).",
                "status": "paper_fill_recorded",
                "execution_enabled": False,
                "exchange_order_submitted": False,
            })
        except Exception:
            pass


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
    from copy import deepcopy
    original = account
    working = deepcopy(account)
    prices: dict[str, Decimal] = {}
    held_pairs = list(account.get("positions", {}).keys())
    if held_pairs:
        async def _fetch_price(p: str):
            try:
                t = await _market.get_ticker(p)
                return p, D(str(t["last"]))
            except Exception:
                return p, None

        fetched = await asyncio.gather(*(_fetch_price(p) for p in held_pairs))
        for p, val in fetched:
            if val is not None and val > 0:
                prices[p] = val

    # Dynamic profit-locking trailing stop: when a position moves into profit,
    # ratchet stop_loss above average_entry so winning trades lock in gains.
    stops_ratcheted = False
    for pair, pos in working.get("positions", {}).items():
        mark = prices.get(pair)
        if mark is None or mark <= 0:
            continue
        avg_entry = D(str(pos.get("average_entry", "0")))
        if avg_entry <= 0:
            continue
        current_stop = D(str(pos["stop_loss"])) if pos.get("stop_loss") else D("0")
        gain_pct = (mark - avg_entry) / avg_entry * D("100")
        new_stop = None
        if gain_pct >= D("0.35"):
            candidate = (mark * D("0.9988")).quantize(D("0.00000001"), rounding=ROUND_DOWN)
            if candidate > current_stop and candidate < mark:
                new_stop = candidate
        elif gain_pct >= D("0.15"):
            candidate = (avg_entry * D("1.0005")).quantize(D("0.00000001"), rounding=ROUND_DOWN)
            if candidate > current_stop and candidate < mark:
                new_stop = candidate
        if new_stop is not None:
            pos["stop_loss"] = str(new_stop)
            stops_ratcheted = True

    equity = account_equity(working, prices)
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
    metrics_changed = stops_ratcheted or any(
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
    current = account.get("positions", {}).get(pair)
    technical_precheck = _technical_precheck.analyse(candles)
    if technical_precheck.signal == TradeAction.HOLD:
        return {"pair": pair, "decision": "HOLD", "reason": "Deterministic technical pre-check found no entry or exit signal."}
    if technical_precheck.signal == TradeAction.BUY and current:
        return {"pair": pair, "decision": "HOLD", "reason": "A paper position is already open for this pair."}
    if technical_precheck.signal == TradeAction.SELL and not current:
        return {"pair": pair, "decision": "HOLD", "reason": "No open long position exists to close."}

    confidence_floor = D(os.getenv("PAPER_AUTOTRADING_MIN_CONFIDENCE", "0.55"))
    if not D("0.5") <= confidence_floor <= D("1"):
        return {"pair": pair, "decision": "HOLD", "reason": "Autonomous confidence threshold is outside the safe 0.5–1.0 range."}

    # Spend model calls when deterministic indicators show a compatible
    # candidate entry or exit; if the LLM stage times out or hesitates on a
    # confirmed deterministic signal, fall back to deterministic technical
    # parameters while keeping the DeterministicRiskEngine authoritative.
    cycle = None
    if os.getenv("PAPER_AUTOTRADING_USE_LLM", "true").lower() == "true":
        try:
            cycle = await asyncio.wait_for(
                _orchestrator.run(
                    pair=pair,
                    ticker=ticker,
                    candles=candles,
                    portfolio=portfolio,
                    closed_trades=account.get("orders", []),
                ),
                timeout=float(os.getenv("PAPER_AUTOTRADING_PAIR_TIMEOUT_SECONDS", "22")),
            )
        except Exception as exc:
            logger.warning("paper_autopilot_llm_fallback pair=%s error_type=%s", pair, type(exc).__name__)
            cycle = None

    if cycle is not None:
        action = cycle.strategy.action
        confidence = D(str(cycle.strategy.confidence))
        technical_signal = cycle.technical_analysis.signal
        atr_val = cycle.technical_analysis.atr
        rationale = cycle.strategy.rationale
        if action == TradeAction.HOLD and technical_signal in {TradeAction.BUY, TradeAction.SELL}:
            action = technical_signal
            confidence = max(confidence, D("0.72"))
            rationale = (
                f"[DETERMINISTIC TECHNICAL EXECUTION] {rationale} "
                f"Confirmed {technical_signal.value} on {cycle.technical_analysis.trend} ({', '.join(cycle.technical_analysis.evidence)})."
            )
    else:
        action = technical_precheck.signal
        confidence = D("0.72")
        technical_signal = technical_precheck.signal
        atr_val = technical_precheck.atr
        rationale = (
            f"Deterministic {technical_precheck.trend} signal ({', '.join(technical_precheck.evidence)}) "
            f"verified against risk policy."
        )

    signal_report = whipsaw_protection.evaluate_signal_quality(candles, account.get("orders", []), action.value)
    analysis = {
        "strategy": cycle.strategy.model_dump(mode="json") if cycle else {
            "action": action.value,
            "confidence": float(confidence),
            "rationale": rationale,
        },
        "technical_analysis": (cycle.technical_analysis if cycle else technical_precheck).model_dump(mode="json"),
        "risk_assessment": cycle.risk_assessment.model_dump(mode="json") if cycle else {"summary": "Deterministic risk gate active"},
        "execution_assessment": cycle.execution_assessment.model_dump(mode="json") if cycle else {"status": "paper_simulation"},
        "performance": cycle.performance_context if cycle else {},
        "signal_quality": signal_report,
    }
    if signal_report.get("action_recommendation") == "FORCE_HOLD":
        action = TradeAction.HOLD

    if confidence < confidence_floor or action == TradeAction.HOLD:
        return {"pair": pair, "decision": "HOLD", "reason": "Confidence or signal-quality threshold not met.", "analysis": analysis}

    if action == TradeAction.BUY:
        if technical_signal != TradeAction.BUY or current:
            return {"pair": pair, "decision": "HOLD", "reason": "Technical confirmation missing or position already open."}
        if not atr_val or atr_val <= 0:
            return {"pair": pair, "decision": "HOLD", "reason": "ATR unavailable; safe stop distance cannot be calculated."}

        price = D(str(ticker["last"]))
        from paper_trading.engine import simulation_settings
        fee_rate, slippage_bps = simulation_settings()
        slippage = slippage_bps / D("10000")
        entry_estimate = price * (D("1") + slippage)
        stop_distance = max(D(str(atr_val)) * D("1.2"), entry_estimate * D("0.0015"))
        stop = entry_estimate - stop_distance
        target = entry_estimate + stop_distance * D("1.8")
        policy = RiskPolicy.from_env()
        if policy is None:
            return {"pair": pair, "decision": "REJECTED", "reason": "Risk policy is missing or invalid."}
        max_position_pct = D(os.getenv("PAPER_AUTOTRADING_MAX_POSITION_PCT", "20"))
        allocatable_cash = min(
            D(str(account["cash"])) * D("0.995"),
            portfolio.equity * max_position_pct / D("100"),
        )
        if allocatable_cash < D("5"):
            return {"pair": pair, "decision": "HOLD", "reason": "Available cash or position allocation budget is below $5 minimum."}
        quantity = calculate_spot_quantity(
            portfolio.equity,
            allocatable_cash,
            entry_estimate,
            stop,
            policy.max_trade_risk_pct * D("0.995"),
            fee_rate,
        )
        if quantity <= 0 or (quantity * entry_estimate) < D("2"):
            return {"pair": pair, "decision": "HOLD", "reason": "Risk-sized quantity is below supported precision or minimum notional."}

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
            "strategy_rationale": rationale[:1000],
            "technical_analysis": analysis.get("technical_analysis"),
            "stop_loss": str(stop),
            "take_profit": str(target),
        })
        return {"pair": pair, "decision": "BUY", "fill": fill, "account_version": saved.get("version"), "analysis": analysis}

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
            "strategy_rationale": rationale[:1000],
            "technical_analysis": analysis.get("technical_analysis"),
        })
        return {"pair": pair, "decision": "SELL", "fill": fill, "account_version": saved.get("version"), "analysis": analysis}

    return {"pair": pair, "decision": "HOLD", "reason": "No compatible open position for this signal.", "analysis": analysis}


def _opportunity_score(pair: str, ticker: dict, candles: list) -> float:
    """Rank candidate pairs by short-term positive momentum and trend alignment."""
    try:
        tech = _technical_precheck.analyse(candles)
        if tech.signal != TradeAction.BUY:
            return -999.0
        closes = [float(c["close"]) for c in candles[-6:] if float(c.get("close", 0)) > 0]
        short_mom = ((closes[-1] - closes[0]) / closes[0] * 100.0) if len(closes) >= 2 else 0.0
        ema_spread = (
            ((tech.ema_fast - tech.ema_slow) / tech.ema_slow * 100.0)
            if (tech.ema_fast and tech.ema_slow and tech.ema_slow > 0)
            else 0.0
        )
        rsi_bonus = 1.5 if (tech.rsi_14 and 50.0 <= tech.rsi_14 <= 66.0) else 0.3
        chg = float(ticker.get("change_percent", 0.0))
        return round(short_mom * 3.0 + ema_spread * 2.0 + chg * 0.5 + rsi_bonus, 4)
    except Exception:
        return -999.0


async def run_autopilot_cycle(db=None) -> dict:
    """Run one autonomous paper cycle; caller must hold the worker lease."""
    if os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true":
        return {"status": "disabled", "reason": "Paper trading is disabled."}
    if not os.getenv("PAPER_API_TOKEN") or not os.getenv("PAPER_INITIAL_BALANCE_USD"):
        return {"status": "disabled", "reason": "Paper account configuration is incomplete."}
    if not _enabled_by_operator():
        return {"status": "disabled", "reason": "PAPER_AUTOTRADING_ALLOWED is false."}

    if db is None:
        db = await get_database()
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
        pairs = configured_pairs()
        sem = asyncio.Semaphore(6)
        candle_interval = int(os.getenv("PAPER_AUTOTRADING_CANDLE_INTERVAL", "60"))

        async def _load_pair_data(p: str):
            async with sem:
                try:
                    t, c = await asyncio.gather(
                        _market.get_ticker(p),
                        _market.get_ohlc(p, interval=candle_interval),
                    )
                    return p, t, c, None
                except Exception as exc:
                    return p, None, None, exc

        loaded = await asyncio.gather(*(_load_pair_data(p) for p in pairs))
        # Prioritize: (1) currently held positions (to check exits), then
        # (2) top-scoring candidate BUY opportunities diversified across asset classes
        held_items = []
        candidate_by_cat: dict[str, list[tuple[float, str, dict, list]]] = {}
        failed_items = []
        for p, t, c, err in loaded:
            if err is not None or t is None or c is None:
                failed_items.append((p, err))
                continue
            if p in account.get("positions", {}):
                held_items.append((p, t, c))
            else:
                score = _opportunity_score(p, t, c)
                cat = instrument_category(p)
                candidate_by_cat.setdefault(cat, []).append((score, p, t, c))

        for cat_list in candidate_by_cat.values():
            cat_list.sort(key=lambda x: x[0], reverse=True)

        # Interleave the #1 best setup from each asset class (forex, metals, indices, crypto),
        # followed by remaining setups sorted by opportunity score.
        ordered_candidates: list[tuple[str, dict, list]] = []
        for cat in ("metals", "indices", "forex", "crypto"):
            if candidate_by_cat.get(cat):
                top = candidate_by_cat[cat].pop(0)
                ordered_candidates.append((top[1], top[2], top[3]))
        remaining = [item for sub in candidate_by_cat.values() for item in sub]
        remaining.sort(key=lambda x: x[0], reverse=True)
        for _, p, t, c in remaining:
            ordered_candidates.append((p, t, c))

        for p, _err in failed_items:
            results.append({"pair": p, "decision": "SKIPPED", "reason": "Provider, analysis or paper execution failed closed."})

        for pair, ticker, candles in [*held_items, *ordered_candidates]:
            try:
                result = await _execute_signal(db, account, pair, ticker, candles, portfolio, held_prices)
                results.append(result)
                if result.get("decision") in {"BUY", "SELL"}:
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


async def run_autopilot_once(db=None) -> dict:
    """Operator-triggered immediate autopilot cycle."""
    if db is None:
        db = await get_database()
    await _acquire_worker_lease(db)
    try:
        return await run_autopilot_cycle(db)
    finally:
        await _release_worker_lease(db)


async def _worker_loop() -> None:
    monitor_interval = max(10, min(60, int(os.getenv("PAPER_AUTOTRADING_MONITOR_SECONDS", "20"))))
    scan_interval = max(60, min(1800, int(os.getenv("PAPER_AUTOTRADING_SCAN_SECONDS", "300"))))
    last_scan: float | None = None
    while True:
        try:
            if os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true" or not os.getenv("PAPER_INITIAL_BALANCE_USD"):
                await asyncio.sleep(monitor_interval)
                continue
            db = await get_database()
            state = await db.paper_runtime.find_one({"_id": "autopilot"})
            if os.getenv("PAPER_TRADING_ENABLED", "false").lower() == "true" and os.getenv("PAPER_INITIAL_BALANCE_USD"):
                if await _acquire_worker_lease(db):
                    try:
                        if state and state.get("enabled") is True and _enabled_by_operator():
                            now = asyncio.get_running_loop().time()
                            if last_scan is None or (now - last_scan >= scan_interval):
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
    if enabled and (not _enabled_by_operator() or os.getenv("PAPER_TRADING_ENABLED", "false").lower() != "true" or not os.getenv("PAPER_API_TOKEN") or not os.getenv("PAPER_INITIAL_BALANCE_USD")):
        raise PaperTradeError("Autonomous paper trading is not permitted by server configuration.")
    if enabled and RiskPolicy.from_env() is None:
        raise PaperTradeError("A complete deterministic risk policy is required before starting the autopilot.")
    if enabled:
        configured_pairs()
    record = {
        "_id": "autopilot",
        "enabled": enabled,
        "updated_at": _utcnow().isoformat(),
        "mode": "paper",
        "exchange_order_submitted": False,
    }
    fields = {key: value for key, value in record.items() if key != "_id"}
    await db.paper_runtime.update_one({"_id": "autopilot"}, {"$set": fields}, upsert=True)
    return record


async def autopilot_status(db) -> dict:
    state = await db.paper_runtime.find_one({"_id": "autopilot"}) or {"enabled": False}
    return {
        "enabled": state.get("enabled") is True,
        "worker_configured": _enabled_by_operator(),
        "worker_running": _worker_task is not None and not _worker_task.done(),
        "paper_trading_enabled": os.getenv("PAPER_TRADING_ENABLED", "false").lower() == "true",
        "monitor_interval_seconds": max(10, min(60, int(os.getenv("PAPER_AUTOTRADING_MONITOR_SECONDS", "20")))),
        "scan_interval_seconds": max(60, min(1800, int(os.getenv("PAPER_AUTOTRADING_SCAN_SECONDS", "300")))),
        "pairs": configured_pairs(),
        "execution_mode": "paper",
        "live_execution_enabled": False,
    }
