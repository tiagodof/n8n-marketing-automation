"""
Unit tests — Meta Ads Client
Module 01: AI Marketing Reporting Agent
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMetaAdsEnvironmentValidation(unittest.TestCase):
    """Verify that the client raises clear errors when credentials are missing."""

    def _import_fresh(self):
        if "scripts.meta_ads_client" in sys.modules:
            del sys.modules["scripts.meta_ads_client"]
        from scripts import meta_ads_client
        return meta_ads_client

    def test_missing_access_token_raises(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID")}
        with patch.dict(os.environ, env, clear=True):
            client = self._import_fresh()
            with self.assertRaises(EnvironmentError):
                client.fetch_weekly_summary()

    def test_missing_account_id_raises(self):
        env = {**os.environ, "META_ACCESS_TOKEN": "fake_token"}
        env.pop("META_AD_ACCOUNT_ID", None)
        with patch.dict(os.environ, env, clear=True):
            client = self._import_fresh()
            with self.assertRaises(EnvironmentError):
                client.fetch_weekly_summary()


class TestMetaAdsDataShape(unittest.TestCase):
    """Verify the shape and types of the returned data structure."""

    MOCK = {
        "period": {"start": "2026-06-19", "end": "2026-06-25"},
        "totals": {
            "spend": 1240.50,
            "impressions": 85000,
            "clicks": 1020,
            "ctr": 1.2,
        },
        "campaigns": [
            {
                "name": "Brand Awareness Q2",
                "spend": 720.00,
                "impressions": 50000,
                "clicks": 600,
                "ctr": 1.2,
                "roas": 3.4,
            },
            {
                "name": "Retargeting — Blog Visitors",
                "spend": 520.50,
                "impressions": 35000,
                "clicks": 420,
                "ctr": 1.2,
                "roas": 4.1,
            },
        ],
    }

    def test_period_keys_present(self):
        self.assertIn("start", self.MOCK["period"])
        self.assertIn("end", self.MOCK["period"])

    def test_totals_keys_present(self):
        for key in ("spend", "impressions", "clicks", "ctr"):
            self.assertIn(key, self.MOCK["totals"])

    def test_campaigns_is_list(self):
        self.assertIsInstance(self.MOCK["campaigns"], list)

    def test_campaign_keys_present(self):
        for campaign in self.MOCK["campaigns"]:
            for key in ("name", "spend", "impressions", "clicks", "ctr", "roas"):
                self.assertIn(key, campaign)

    def test_campaigns_sorted_by_spend_desc(self):
        spends = [c["spend"] for c in self.MOCK["campaigns"]]
        self.assertEqual(spends, sorted(spends, reverse=True))

    def test_total_spend_is_positive(self):
        self.assertGreater(self.MOCK["totals"]["spend"], 0)

    def test_ctr_is_valid_percentage(self):
        ctr = self.MOCK["totals"]["ctr"]
        self.assertGreaterEqual(ctr, 0)
        self.assertLessEqual(ctr, 100)

    def test_roas_is_non_negative(self):
        for campaign in self.MOCK["campaigns"]:
            self.assertGreaterEqual(campaign["roas"], 0)


class TestMetaAdsAPICall(unittest.TestCase):
    """Verify the API call is constructed correctly."""

    def test_api_call_uses_correct_endpoint(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {
            "META_ACCESS_TOKEN": "fake_token",
            "META_AD_ACCOUNT_ID": "act_123456",
        }):
            with patch("requests.get", return_value=mock_response) as mock_get:
                if "scripts.meta_ads_client" in sys.modules:
                    del sys.modules["scripts.meta_ads_client"]
                from scripts import meta_ads_client
                meta_ads_client.fetch_weekly_summary()

                call_args = mock_get.call_args
                self.assertIn("act_123456/insights", call_args[0][0])

    def test_empty_response_returns_zero_totals(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {
            "META_ACCESS_TOKEN": "fake_token",
            "META_AD_ACCOUNT_ID": "act_123456",
        }):
            with patch("requests.get", return_value=mock_response):
                if "scripts.meta_ads_client" in sys.modules:
                    del sys.modules["scripts.meta_ads_client"]
                from scripts import meta_ads_client
                result = meta_ads_client.fetch_weekly_summary()

                self.assertEqual(result["totals"]["spend"], 0.0)
                self.assertEqual(result["totals"]["impressions"], 0)
                self.assertEqual(result["campaigns"], [])


if __name__ == "__main__":
    unittest.main()
