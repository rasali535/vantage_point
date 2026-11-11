import unittest
from decimal import Decimal
from unittest.mock import patch

from paper_trading.engine import (
    PaperTradeError, account_summary, initial_account, simulate_order,
    evaluate_protective_triggers,
)
from risk.engine import DeterministicRiskEngine, RiskPolicy


def policy():
    return RiskPolicy(
        max_trade_risk_pct=Decimal("1"),
        max_daily_loss_pct=Decimal("5"),
        max_drawdown_pct=Decimal("10"),
        max_open_positions=5,
        max_leverage=Decimal("1"),
        require_stop_loss=True,
    )


class PaperTradingTests(unittest.TestCase):
    def setUp(self):
        self.account = initial_account("10000")

    def buy(self, key="buy-1", qty="0.01", stop="49000"):
        return simulate_order(
            self.account, pair="BTC/USD", side="BUY", quantity=qty,
            reference_price="50000", idempotency_key=key,
            stop_loss_price=stop, risk_engine=DeterministicRiskEngine(policy()),
        )

    def test_buy_creates_virtual_position_and_never_submits_exchange_order(self):
        account, fill = self.buy()
        self.assertEqual(fill["status"], "filled")
        self.assertFalse(fill["exchange_order_submitted"])
        self.assertEqual(account["mode"], "paper")
        self.assertIn("BTC/USD", account["positions"])
        self.assertLess(Decimal(account["cash"]), Decimal("10000"))

    def test_idempotency_returns_existing_fill_without_double_debit(self):
        first, fill = self.buy()
        second, duplicate = simulate_order(
            first, pair="BTC/USD", side="BUY", quantity="0.01",
            reference_price="50000", idempotency_key="buy-1",
            stop_loss_price="49000", risk_engine=DeterministicRiskEngine(policy()),
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(second["cash"], first["cash"])
        self.assertEqual(len(second["orders"]), 1)

    def test_missing_policy_rejects_buy(self):
        with self.assertRaisesRegex(PaperTradeError, "Risk policy"):
            simulate_order(
                self.account, pair="BTC/USD", side="BUY", quantity="0.01",
                reference_price="50000", idempotency_key="no-policy",
                stop_loss_price="49000", risk_engine=DeterministicRiskEngine(),
            )

    def test_stop_loss_risk_breach_rejects_buy(self):
        with self.assertRaisesRegex(PaperTradeError, "Risk gate rejected"):
            simulate_order(
                self.account, pair="BTC/USD", side="BUY", quantity="0.1",
                reference_price="50000", idempotency_key="too-large",
                stop_loss_price="40000", risk_engine=DeterministicRiskEngine(policy()),
            )

    def test_cannot_sell_more_than_held_or_open_short(self):
        account, _ = self.buy()
        with self.assertRaisesRegex(PaperTradeError, "exceeds the held"):
            simulate_order(
                account, pair="BTC/USD", side="SELL", quantity="0.02",
                reference_price="51000", idempotency_key="oversell",
            )

    def test_sell_closes_position_and_records_realized_pnl(self):
        account, _ = self.buy()
        account, fill = simulate_order(
            account, pair="BTC/USD", side="SELL", quantity="0.01",
            reference_price="51000", idempotency_key="sell-1",
        )
        self.assertFalse(fill["exchange_order_submitted"])
        self.assertNotIn("BTC/USD", account["positions"])
        self.assertGreater(Decimal(account["realized_pnl"]), Decimal("0"))

    def test_non_usd_pair_rejected(self):
        with self.assertRaisesRegex(PaperTradeError, "USD-quoted"):
            simulate_order(
                self.account, pair="BTC/EUR", side="BUY", quantity="0.01",
                reference_price="50000", idempotency_key="eur",
                stop_loss_price="49000", risk_engine=DeterministicRiskEngine(policy()),
            )

    def test_summary_is_explicitly_paper_and_not_live(self):
        summary = account_summary(self.account)
        self.assertEqual(summary["mode"], "paper")
        self.assertFalse(summary["execution_enabled"])
        self.assertFalse(summary["exchange_order_submitted"])



    def test_stop_loss_trigger_simulates_exit_and_never_submits_exchange_order(self):
        account, _ = self.buy()
        updated, exits = evaluate_protective_triggers(account, {"BTC/USD": "48000"})
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0]["triggered_by"], "stop_loss")
        self.assertFalse(exits[0]["exchange_order_submitted"])
        self.assertNotIn("BTC/USD", updated["positions"])

    def test_take_profit_trigger_simulates_exit(self):
        account, _ = simulate_order(
            self.account, pair="BTC/USD", side="BUY", quantity="0.01",
            reference_price="50000", idempotency_key="buy-target",
            stop_loss_price="49000", take_profit_price="52000",
            risk_engine=DeterministicRiskEngine(policy()),
        )
        updated, exits = evaluate_protective_triggers(account, {"BTC/USD": "52500"})
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0]["triggered_by"], "take_profit")
        self.assertNotIn("BTC/USD", updated["positions"])

    def test_protective_monitor_does_nothing_when_thresholds_not_crossed(self):
        account, _ = self.buy()
        updated, exits = evaluate_protective_triggers(account, {"BTC/USD": "50500"})
        self.assertEqual(exits, [])
        self.assertEqual(updated["positions"], account["positions"])

    def test_invalid_take_profit_is_rejected(self):
        with self.assertRaisesRegex(PaperTradeError, "take-profit must be above"):
            simulate_order(
                self.account, pair="BTC/USD", side="BUY", quantity="0.01",
                reference_price="50000", idempotency_key="bad-target",
                stop_loss_price="49000", take_profit_price="49000",
                risk_engine=DeterministicRiskEngine(policy()),
            )

if __name__ == "__main__":
    unittest.main()
