"""Unit tests for the LinkedIn Ads client - Module 01."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestLinkedInEnvironmentValidation(unittest.TestCase):
    """Validate required setup values before a network request is made."""

    @staticmethod
    def _fresh_client():
        sys.modules.pop("scripts.linkedin_ads_client", None)
        from scripts import linkedin_ads_client
        return linkedin_ads_client

    def test_missing_access_token_raises(self):
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AD_ACCOUNT_ID")
        }
        with patch.dict(os.environ, environment, clear=True):
            client = self._fresh_client()
            with self.assertRaises(EnvironmentError):
                client.fetch_weekly_summary()

    def test_missing_account_id_raises(self):
        environment = {**os.environ, "LINKEDIN_ACCESS_TOKEN": "test-token"}
        environment.pop("LINKEDIN_AD_ACCOUNT_ID", None)
        with patch.dict(os.environ, environment, clear=True):
            client = self._fresh_client()
            with self.assertRaises(EnvironmentError):
                client.fetch_weekly_summary()

    def test_invalid_campaign_name_mapping_raises(self):
        environment = {
            "LINKEDIN_ACCESS_TOKEN": "test-token",
            "LINKEDIN_AD_ACCOUNT_ID": "12345",
            "LINKEDIN_CAMPAIGN_NAMES": "not-json",
        }
        with patch.dict(os.environ, environment, clear=True):
            client = self._fresh_client()
            with self.assertRaises(EnvironmentError):
                client.fetch_weekly_summary()

    def test_zero_days_raises(self):
        environment = {
            "LINKEDIN_ACCESS_TOKEN": "test-token",
            "LINKEDIN_AD_ACCOUNT_ID": "12345",
        }
        with patch.dict(os.environ, environment, clear=True):
            client = self._fresh_client()
            with self.assertRaises(ValueError):
                client.fetch_weekly_summary(days=0)


class TestLinkedInAnalyticsResponse(unittest.TestCase):
    """Validate normalisation of a representative Ad Analytics response."""

    API_RESPONSE = {
        "elements": [
            {
                "pivotValues": ["urn:li:sponsoredCampaign:987"],
                "impressions": 18000,
                "clicks": 252,
                "costInLocalCurrency": 430.00,
                "landingPageClicks": 198,
                "externalWebsiteConversions": 19,
            },
            {
                "pivotValues": ["urn:li:sponsoredCampaign:654"],
                "impressions": 11000,
                "clicks": 143,
                "costInLocalCurrency": 250.00,
                "landingPageClicks": 99,
                "externalWebsiteConversions": 7,
            },
        ]
    }

    @staticmethod
    def _environment():
        return {
            "LINKEDIN_ACCESS_TOKEN": "test-token",
            "LINKEDIN_AD_ACCOUNT_ID": "12345",
            "LINKEDIN_CAMPAIGN_NAMES": '{"987": "Lead Generation - Q3", "654": "Content Promotion"}',
        }

    @staticmethod
    def _fresh_client():
        sys.modules.pop("scripts.linkedin_ads_client", None)
        from scripts import linkedin_ads_client
        return linkedin_ads_client

    def test_response_shape_and_totals(self):
        mock_response = MagicMock()
        mock_response.json.return_value = self.API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, self._environment(), clear=True):
            with patch("requests.get", return_value=mock_response):
                client = self._fresh_client()
                result = client.fetch_weekly_summary(days=7)

        self.assertEqual(result["totals"]["spend"], 680.00)
        self.assertEqual(result["totals"]["impressions"], 29000)
        self.assertEqual(result["totals"]["clicks"], 395)
        self.assertEqual(result["totals"]["landing_page_clicks"], 297)
        self.assertEqual(result["totals"]["conversions"], 26.00)
        self.assertAlmostEqual(result["totals"]["ctr"], 1.3621)
        self.assertEqual(len(result["campaigns"]), 2)
        self.assertEqual(result["campaigns"][0]["name"], "Lead Generation - Q3")
        self.assertEqual(result["campaigns"][0]["id"], "987")

    def test_api_call_uses_rest_endpoint_and_required_headers(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, self._environment(), clear=True):
            with patch("requests.get", return_value=mock_response) as request_get:
                client = self._fresh_client()
                client.fetch_weekly_summary(days=7)

        call_args = request_get.call_args
        self.assertEqual(call_args.args[0], "https://api.linkedin.com/rest/adAnalytics")
        self.assertEqual(call_args.kwargs["headers"]["Authorization"], "Bearer test-token")
        self.assertIn("LinkedIn-Version", call_args.kwargs["headers"])
        self.assertEqual(call_args.kwargs["headers"]["LinkedIn-Version"], "202608")
        self.assertEqual(call_args.kwargs["params"]["pivot"], "CAMPAIGN")
        self.assertEqual(call_args.kwargs["params"]["timeGranularity"], "ALL")
        self.assertIn("costInLocalCurrency", call_args.kwargs["params"]["fields"])

    def test_empty_response_returns_zero_totals(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, self._environment(), clear=True):
            with patch("requests.get", return_value=mock_response):
                client = self._fresh_client()
                result = client.fetch_weekly_summary()

        self.assertEqual(result["totals"]["spend"], 0.0)
        self.assertEqual(result["totals"]["impressions"], 0)
        self.assertEqual(result["campaigns"], [])


class TestLinkedInHelpers(unittest.TestCase):
    """Validate small deterministic helpers separately."""

    @staticmethod
    def _client():
        sys.modules.pop("scripts.linkedin_ads_client", None)
        from scripts import linkedin_ads_client
        return linkedin_ads_client

    def test_campaign_id_is_extracted_from_urn(self):
        client = self._client()
        self.assertEqual(client._campaign_id("urn:li:sponsoredCampaign:987"), "987")

    def test_campaign_urn_reads_current_pivot_values_shape(self):
        client = self._client()
        element = {"pivotValues": ["urn:li:sponsoredCampaign:987"]}
        self.assertEqual(client._campaign_urn(element), "urn:li:sponsoredCampaign:987")

    def test_campaign_urn_supports_legacy_single_value_shape(self):
        client = self._client()
        element = {"pivotValue": "urn:li:sponsoredCampaign:987"}
        self.assertEqual(client._campaign_urn(element), "urn:li:sponsoredCampaign:987")

    def test_date_range_format(self):
        from datetime import date
        client = self._client()
        date_range = client._date_range_value(date(2026, 8, 1), date(2026, 8, 7))
        self.assertIn("start:(day:1,month:8,year:2026)", date_range)
        self.assertIn("end:(day:7,month:8,year:2026)", date_range)


if __name__ == "__main__":
    unittest.main()
