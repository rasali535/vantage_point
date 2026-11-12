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
SUPPORTED_FIAT_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "NZD"}
SUPPORTED_METALS = {"XAU", "XAG", "XPT", "XPD", "XCU", "PAXG", "XAUT"}
SUPPORTED_INDICES = {"SPX500", "NAS100", "US30", "UK100", "GER40", "JPN225"}


def instrument_category(pair: Any) -> str:
    if not isinstance(pair, str) or "/" not in pair:
        return "other"
    base, _, quote = pair.strip().upper().partition("/")
    if base in SUPPORTED_METALS:
        return "metals"
    if base in SUPPORTED_INDICES:
        return "indices"
    if base in SUPPORTED_FIAT_CURRENCIES and quote in SUPPORTED_FIAT_CURRENCIES:
        return "forex"
    return "crypto"


def is_supported_paper_pair(pair: Any) -> bool:
    if not isinstance(pair, str) or "/" not in pair:
        return False
    base, sep, quote = pair.strip().upper().partition("/")
    if not sep or not base.isalnum() or not quote.isalnum() or base == quote:
        return False
    if quote == "USD":
        return True
    return base in SUPPORTED_FIAT_CURRENCIES and quote in SUPPORTED_FIAT_CURRENCIES


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
    take_profit_price: Any = None,
    risk_engine: DeterministicRiskEngine | None = None,
    portfolio_prices: dict[str, Any] | None = None,
) -> tuple[dict, dict]:
    """Return (new account, simulated fill); caller persists atomically."""
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise PaperTradeError("A non-empty idempotency key of at most 128 characters is required.")
    if not is_supported_paper_pair(pair):
        raise PaperTradeError("Only Forex pairs and USD-quoted spot pairs are supported in paper mode.")
    pair = pair.strip().upper()
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
    if gross <= 0:
        raise PaperTradeError("Order notional value is too small to simulate.")
    fee = _quantize(gross * fee_rate, MONEY_STEP)
    total = gross + fee
    updated = deepcopy(account)
    positions = updated.setdefault("positions", {})
    position = positions.get(pair)
    now_cash = dec(updated["cash"], "cash")

    realized = None
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
        target = dec(take_profit_price, "take_profit_price") if take_profit_price is not None else None
        if stop is not None and stop >= fill_price:
            raise PaperTradeError("BUY stop-loss must be below the simulated fill price.")
        if target is not None and target <= fill_price:
            raise PaperTradeError("BUY take-profit must be above the simulated fill price.")
        if stop is not None and target is not None and stop >= target:
            raise PaperTradeError("Stop-loss must be below take-profit.")
        old_qty = dec(position["quantity"], "position quantity") if position else D("0")
        old_cost = dec(position["average_entry"], "average_entry") * old_qty if position else D("0")
        new_qty = old_qty + qty
        avg = (old_cost + total) / new_qty
        positions[pair] = {
            "quantity": str(_quantize(new_qty, QTY_STEP)),
            "average_entry": str(_quantize(avg, D("0.00000001"))),
            "stop_loss": str(stop) if stop is not None else (position or {}).get("stop_loss"),
            "take_profit": str(target) if target is not None else (position or {}).get("take_profit"),
            "opened_at": (position or {}).get("opened_at") or datetime.now(timezone.utc).isoformat(),
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
        "realized_pnl_usd": str(_quantize(realized, MONEY_STEP)) if realized is not None else None,
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
    unrealized_total = D("0")
    for pair, position in account.get("positions", {}).items():
        quantity = dec(position["quantity"], "quantity")
        avg_entry = dec(position["average_entry"], "average_entry")
        mark = dec(prices.get(pair, position["average_entry"]), "mark price")
        value = quantity * mark
        cost = quantity * avg_entry
        unrealized = value - cost
        unrealized_pct = (unrealized / cost * D("100")) if cost > 0 else D("0")
        market_value += value
        unrealized_total += unrealized
        positions.append({
            **position,
            "pair": pair,
            "category": instrument_category(pair),
            "mark_price": str(mark),
            "market_value": str(_quantize(value, MONEY_STEP)),
            "cost_basis": str(_quantize(cost, MONEY_STEP)),
            "unrealized_pnl_usd": str(_quantize(unrealized, MONEY_STEP)),
            "unrealized_pnl_pct": float(_quantize(unrealized_pct, D("0.01"))),
        })
    equity = cash + market_value
    initial_eq = dec(account.get("initial_equity", equity), "initial_equity")
    realized = dec(account.get("realized_pnl", "0"), "realized_pnl")
    total_pnl = realized + unrealized_total
    total_return_pct = (total_pnl / initial_eq * D("100")) if initial_eq > 0 else D("0")
    return {
        "mode": "paper",
        "currency": "USD",
        "cash": str(cash),
        "initial_equity": str(_quantize(initial_eq, MONEY_STEP)),
        "positions": positions,
        "market_value": str(_quantize(market_value, MONEY_STEP)),
        "equity": str(_quantize(equity, MONEY_STEP)),
        "realized_pnl": account.get("realized_pnl", "0"),
        "unrealized_pnl": str(_quantize(unrealized_total, MONEY_STEP)),
        "total_pnl": str(_quantize(total_pnl, MONEY_STEP)),
        "total_return_pct": float(_quantize(total_return_pct, D("0.01"))),
        "order_count": len(account.get("orders", [])),
        "execution_enabled": False,
        "exchange_order_submitted": False,
    }



def evaluate_protective_triggers(
    account: dict,
    prices: dict[str, Any],
) -> tuple[dict, list[dict]]:
    """Simulate full-position exits when a public mark crosses a stored stop/target."""
    updated = deepcopy(account)
    triggered = []
    for pair, position in list(updated.get("positions", {}).items()):
        if pair not in prices:
            continue
        mark = dec(prices[pair], f"{pair} market price")
        if mark <= 0:
            continue
        stop = dec(position["stop_loss"], "stop_loss") if position.get("stop_loss") is not None else None
        target = dec(position["take_profit"], "take_profit") if position.get("take_profit") is not None else None
        reason = "stop_loss" if stop is not None and mark <= stop else (
            "take_profit" if target is not None and mark >= target else None
        )
        if reason is None:
            continue
        key = f"protective:{pair}:{reason}:{position.get('opened_at') or position.get('quantity')}"
        updated, fill = simulate_order(
            updated,
            pair=pair,
            side="SELL",
            quantity=position["quantity"],
            reference_price=mark,
            idempotency_key=key,
        )
        fill["triggered_by"] = reason
        fill["trigger_price"] = str(stop if reason == "stop_loss" else target)
        # Replace the just-created order with the enriched protective-trigger record.
        updated["orders"][-1] = {k: v for k, v in fill.items() if k != "duplicate"}
        triggered.append(fill)
    return updated, triggered
