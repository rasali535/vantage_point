import unittest

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from paper_trading.autopilot import _market_error_summary, _worker_identity, _worker_lease_diagnostic, _worker_owner


class MarketDataDiagnosticsTests(unittest.TestCase):
    def test_market_error_summary_keeps_status_and_redacts_credentials(self):
        detail = _market_error_summary(RuntimeError(
            "Exness API returned HTTP 401; access_token=super-secret Bearer abc123"
        ))
        self.assertIn("HTTP 401", detail)
        self.assertIn("access_token=[redacted]", detail)
        self.assertIn("Bearer [redacted]", detail)
        self.assertNotIn("super-secret", detail)
        self.assertNotIn("abc123", detail)

    def test_market_error_summary_is_bounded_and_handles_empty_messages(self):
        self.assertEqual(_market_error_summary(RuntimeError("")), "No error detail supplied.")
        self.assertLessEqual(len(_market_error_summary(RuntimeError("x" * 500))), 240)

    def test_worker_lease_diagnostic_reports_database_and_active_conflict_without_owner(self):
        now = datetime.now(timezone.utc)
        lease = {
            "owner": "another-worker-secret-id",
            "status": "running",
            "expires_at": (now + timedelta(minutes=5)).replace(tzinfo=None),
        }
        details = _worker_lease_diagnostic(SimpleNamespace(name="vantage_point"), lease, now)
        self.assertEqual(details["database"], "vantage_point")
        self.assertTrue(details["lease_found"])
        self.assertTrue(details["lease_expiry_active"])
        self.assertFalse(details["owner_matches_this_worker"])
        self.assertNotIn("owner", details)
        self.assertNotIn("another-worker-secret-id", str(details))
        self.assertEqual(details["worker_identity"], None)

    def test_worker_identity_contains_platform_fields_without_owner_secret(self):
        identity = _worker_identity()
        self.assertIn("service_id", identity)
        self.assertIn("instance_id", identity)
        self.assertIn("deploy_commit", identity)
        self.assertEqual(len(identity["process_id"]), 12)
        self.assertNotIn(_worker_owner, str(identity))


if __name__ == "__main__":
    unittest.main()
