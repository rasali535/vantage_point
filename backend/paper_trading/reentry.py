"""Entry cooldowns after paper exits to prevent immediate whipsaw re-entry."""
from datetime import datetime, timezone
import math
import os


def _configured_seconds(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def reentry_cooldown_remaining(orders: list[dict], pair: str, now: datetime | None = None) -> int:
    """Seconds remaining before re-entering a pair after its latest filled SELL."""
    pair = str(pair).upper()
    last_exit = next(
        (
            order for order in reversed(orders)
            if str(order.get("pair", "")).upper() == pair
            and str(order.get("side", "")).upper() == "SELL"
            and str(order.get("status", "filled")).lower() == "filled"
        ),
        None,
    )
    if not last_exit:
        return 0

    order_id = str(last_exit.get("idempotency_key") or last_exit.get("id") or "")
    stop_exit = (
        str(last_exit.get("triggered_by", "")).lower() == "stop_loss"
        or ":stop_loss:" in order_id
    )
    cooldown = (
        _configured_seconds("PAPER_AUTOTRADING_STOP_COOLDOWN_SECONDS", 900, 60, 86400)
        if stop_exit
        else _configured_seconds("PAPER_AUTOTRADING_REENTRY_COOLDOWN_SECONDS", 180, 30, 3600)
    )

    raw_timestamp = last_exit.get("timestamp")
    try:
        exited_at = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
        if exited_at.tzinfo is None:
            exited_at = exited_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        # Missing or malformed exit time must fail closed, not permit instant re-entry.
        return cooldown

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    elapsed = (current_time - exited_at).total_seconds()
    if elapsed < 0:
        return cooldown
    return max(0, math.ceil(cooldown - elapsed))
