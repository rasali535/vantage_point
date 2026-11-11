"""Deterministic spot paper-trading domain engine.

All fills are simulations against a supplied public-market reference price.
This module has no Kraken client, credentials, network access, or live-order path.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import os
from typing import Any

from risk.engine import DeterministicRiskEngine, OrderProposal, RiskPolicy

D = Decimal
QTY_STEP = D("0.00000001")
MONEY_STEP = D("0.01")


class PaperTradeError(ValueError):
    pass


def dec(value: Any, field: str) -> Decimal:
    try:
        result = D(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise PaperTradeError(f"{field} must be a valid decimal.")
    if not result.is_finite():
        raise PaperTradeError(f"{field} must be finite.")
    return result


def _quantize(value: Decimal, step: Decimal) -> Decimal:
    return value.quantize(step, rounding=ROUND_DOWN)


def simulation_settings() -> tuple[Decimal, Decimal]:
    """Return fee rate and slippage basis points; both are simulation assumptions."""
    fee = dec(os.getenv("PAPER_FEE_RATE", "0.0026"), "PAPER_FEE_RATE")
    slippage = dec(os.getenv("PAPER_SLIPPAGE_BPS", "5"), "PAPER_SLIPPAGE_BPS")
    if fee < 0 or fee >= 1 or slippage < 0 or slippage > 500:
        raise PaperTradeError("Paper fee or slippage configuration is outside safe bounds.")
    return fee, slippage


def initial_account(initial_cash: Any) -> dict:
    cash = dec(initial_cash, "initial_cash")
    if cash <= 0:
        raise PaperTradeError("Initial paper balance must be positive.")
    cash = _quantize(cash, MONEY_STEP)
    return {
        "_id": "default",
        "mode": "paper",
        "currency": "USD",
        "cash": str(cash),
        "positions": {},
        "orders": [],
        "version": 0,
        "initial_equity": str(cash),
        "peak_equity": str(cash),
        "day_start_equity": str(cash),
        "day_start_date": datetime.now(timezone.utc).date().isoformat(),
        "realized_pnl": "0",
        "execution_enabled": False,
    }


def account_equity(account: dict, prices: dict[str, Any]) -> Decimal:
    equity = dec(account["cash"], "cash")
    for pair, position in account.get("positions", {}).items():
        price = dec(prices.get(pair, position.get("average_entry")), f"{pair} market price")
        equity += dec(position["quantity"], "position quantity") * price
    return equity


def simulate_order(
    account: dict,
    *,
    pair: str,
    side: str,
    quantity: Any,
    reference_price: Any,
    idempotency_key: str,
    stop_loss_price: Any = None,
    risk_engine: DeterministicRiskEngine | None = None,
    portfolio_prices: dict[str, Any] | None = None,
) -> tuple[dict, dict]:
    """Return (new account, simulated fill); caller persists atomically."""
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise PaperTradeError("A non-empty idempotency key of at most 128 characters is required.")
    if not isinstance(pair, str) or "/" not in pair or pair.split("/")[-1] != "USD":
        raise PaperTradeError("Only USD-quoted spot pairs are supported in paper mode.")
    side = str(side).upper()
    if side not in {"BUY", "SELL"}:
        raise PaperTradeError("Side must be BUY or SELL.")
    qty = _quantize(dec(quantity, "quantity"), QTY_STEP)
    price = dec(reference_price, "reference_price")
    if qty <= 0 or price <= 0:
        raise PaperTradeError("Quantity and reference price must be positive.")

    previous = next((o for o in account.get("orders", []) if o.get("idempotency_key") == idempotency_key), None)
    if previous:
        return deepcopy(account), {**previous, "duplicate": True}

    fee_rate, slippage_bps = simulation_settings()
    slip = slippage_bps / D("10000")
    fill_price = price * (D("1") + slip if side == "BUY" else D("1") - slip)
    fill_price = _quantize(fill_price, D("0.00000001"))
    gross = _quantize(qty * fill_price, MONEY_STEP)
    fee = _quantize(gross * fee_rate, MONEY_STEP)
    total = gross + fee
    updated = deepcopy(account)
    positions = updated.setdefault("positions", {})
    position = positions.get(pair)
    now_cash = dec(updated["cash"], "cash")

    if side == "BUY":
        if now_cash < total:
            raise PaperTradeError("Insufficient paper USD balance for this order and fee.")
        stop = dec(stop_loss_price, "stop_loss_price") if stop_loss_price is not None else None
        policy = (risk_engine or DeterministicRiskEngine()).policy or RiskPolicy.from_env()
        if policy is None:
            raise PaperTradeError("Risk policy is missing or invalid; paper BUY rejected.")
        if policy.require_stop_loss and stop is None:
            raise PaperTradeError("A stop-loss is required by the configured risk policy.")
        prices = dict(portfolio_prices or {})
        prices[pair] = price
        equity = account_equity(updated, prices)
        initial = dec(updated.get("initial_equity", equity), "initial_equity")
        peak = max(dec(updated.get("peak_equity", equity), "peak_equity"), equity)
        today = datetime.now(timezone.utc).date().isoformat()
        if updated.get("day_start_date") != today:
            updated["day_start_date"] = today
            updated["day_start_equity"] = str(equity)
        day_start = dec(updated.get("day_start_equity", initial), "day_start_equity")
        updated["peak_equity"] = str(peak)
        daily_loss = max(D("0"), (day_start - equity) / day_start * D("100")) if day_start > 0 else D("0")
        drawdown = max(D("0"), (peak - equity) / peak * D("100")) if peak > 0 else D("0")
        positions_count = sum(1 for p in positions.values() if dec(p["quantity"], "position quantity") > 0)
        risk = (risk_engine or DeterministicRiskEngine()).evaluate(OrderProposal(
            pair=pair, side="BUY", quantity=qty, entry_price=fill_price,
            equity=equity, stop_loss_price=stop, daily_loss_pct=daily_loss,
            drawdown_pct=drawdown, open_positions=positions_count,
            leverage=D("1"),
        ))
        if not risk.get("approved"):
            raise PaperTradeError("Risk gate rejected paper BUY: " + "; ".join(risk.get("reasons", [])))
        if stop is not None and stop >= fill_price:
            raise PaperTradeError("BUY stop-loss must be below the simulated fill price.")
        old_qty = dec(position["quantity"], "position quantity") if position else D("0")
        old_cost = dec(position["average_entry"], "average_entry") * old_qty if position else D("0")
        new_qty = old_qty + qty
        avg = (old_cost + total) / new_qty
        positions[pair] = {
            "quantity": str(_quantize(new_qty, QTY_STEP)),
            "average_entry": str(_quantize(avg, D("0.00000001"))),
            "stop_loss": str(stop) if stop is not None else (position or {}).get("stop_loss"),
            "opened_at": (position or {}).get("opened_at"),
        }
        updated["cash"] = str(_quantize(now_cash - total, MONEY_STEP))
    else:
        if not position:
            raise PaperTradeError("No paper position exists for this pair to sell.")
        held = dec(position["quantity"], "position quantity")
        if qty > held:
            raise PaperTradeError("Paper SELL quantity exceeds the held spot position; shorting is disabled.")
        proceeds = gross - fee
        avg_entry = dec(position["average_entry"], "average_entry")
        realized = (fill_price - avg_entry) * qty - fee
        updated["cash"] = str(_quantize(now_cash + proceeds, MONEY_STEP))
        updated["realized_pnl"] = str(_quantize(dec(updated.get("realized_pnl", "0"), "realized_pnl") + realized, MONEY_STEP))
        remaining = held - qty
        if remaining == 0:
            positions.pop(pair, None)
        else:
            position["quantity"] = str(_quantize(remaining, QTY_STEP))

    fill = {
        "id": idempotency_key,
        "idempotency_key": idempotency_key,
        "pair": pair,
        "side": side,
        "quantity": str(qty),
        "reference_price": str(price),
        "fill_price": str(fill_price),
        "gross_usd": str(gross),
        "fee_usd": str(fee),
        "fee_rate": str(fee_rate),
        "slippage_bps": str(slippage_bps),
        "status": "filled",
        "execution_mode": "paper",
        "exchange_order_submitted": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    updated["orders"] = updated.get("orders", []) + [fill]
    updated["version"] = int(updated.get("version", 0)) + 1
    return updated, {**fill, "duplicate": False}


def account_summary(account: dict, prices: dict[str, Any] | None = None) -> dict:
    prices = prices or {}
    cash = dec(account["cash"], "cash")
    positions = []
    market_value = D("0")
    for pair, position in account.get("positions", {}).items():
        quantity = dec(position["quantity"], "quantity")
        mark = dec(prices.get(pair, position["average_entry"]), "mark price")
        value = quantity * mark
        market_value += value
        positions.append({**position, "pair": pair, "mark_price": str(mark), "market_value": str(_quantize(value, MONEY_STEP))})
    return {
        "mode": "paper",
        "currency": "USD",
        "cash": str(cash),
        "positions": positions,
        "market_value": str(_quantize(market_value, MONEY_STEP)),
        "equity": str(_quantize(cash + market_value, MONEY_STEP)),
        "realized_pnl": account.get("realized_pnl", "0"),
        "order_count": len(account.get("orders", [])),
        "execution_enabled": False,
        "exchange_order_submitted": False,
    }
