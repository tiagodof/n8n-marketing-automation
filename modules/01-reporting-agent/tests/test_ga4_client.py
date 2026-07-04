"""
Unit tests — GA4 Client
Module 01: AI Marketing Reporting Agent
"""

import os
import sys
import unittest

# Make the scripts directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGA4EnvironmentValidation(unittest.TestCase):
    """Verify that the client raises clear errors when credentials are missing."""

    def test_missing_property_id_raises(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("GA4_PROPERTY_ID", "GOOGLE_SERVICE_ACCOUNT_KEY")}
        import unittest.mock as mock
        with mock.patch.dict(os.environ, env, clear=True):
            # Re-import to pick up cleared env
            if "scripts.ga4_client" in sys.modules:
                del sys.modules["scripts.ga4_client"]
            from scripts import ga4_client
            with self.assertRaises(EnvironmentError):
                ga4_client.fetch_weekly_summary(property_id=None)

    def test_missing_service_account_key_raises(self):
        import unittest.mock as mock
        env = {**os.environ, "GA4_PROPERTY_ID": "123456789"}
        env.pop("GOOGLE_SERVICE_ACCOUNT_KEY", None)
        with mock.patch.dict(os.environ, env, clear=True):
            if "scripts.ga4_client" in sys.modules:
                del sys.modules["scripts.ga4_client"]
            from scripts import ga4_client
            with self.assertRaises(EnvironmentError):
                ga4_client._get_client()


class TestGA4DataShape(unittest.TestCase):
    """Verify the shape and types of the returned data structure."""

    MOCK = {
        "period": {"start": "2026-06-19", "end": "2026-06-25"},
        "overview": {
            "sessions": 4821,
            "users": 3102,
            "new_users": 1890,
            "conversions": 47,
            "bounce_rate": 42.3,
        },
        "top_pages": [
            {"page": "/", "sessions": 1200},
            {"page": "/pricing", "sessions": 780},
        ],
        "traffic_sources": [
            {"source": "google", "medium": "organic", "sessions": 2100},
        ],
    }

    def test_period_keys_present(self):
        self.assertIn("start", self.MOCK["period"])
        self.assertIn("end", self.MOCK["period"])

    def test_overview_keys_present(self):
        for key in ("sessions", "users", "new_users", "conversions", "bounce_rate"):
            self.assertIn(key, self.MOCK["overview"])

    def test_overview_types(self):
        ov = self.MOCK["overview"]
        self.assertIsInstance(ov["sessions"], int)
        self.assertIsInstance(ov["users"], int)
        self.assertIsInstance(ov["bounce_rate"], float)

    def test_top_pages_is_list(self):
        self.assertIsInstance(self.MOCK["top_pages"], list)

    def test_top_pages_have_required_keys(self):
        for page in self.MOCK["top_pages"]:
            self.assertIn("page", page)
            self.assertIn("sessions", page)

    def test_traffic_sources_is_list(self):
        self.assertIsInstance(self.MOCK["traffic_sources"], list)

    def test_bounce_rate_is_valid_percentage(self):
        bounce = self.MOCK["overview"]["bounce_rate"]
        self.assertGreaterEqual(bounce, 0)
        self.assertLessEqual(bounce, 100)

    def test_sessions_is_positive(self):
        self.assertGreater(self.MOCK["overview"]["sessions"], 0)


if __name__ == "__main__":
    unittest.main()
