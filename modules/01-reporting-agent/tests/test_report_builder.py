"""Unit tests for the AI marketing report builder - Module 01."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class ReportBuilderFixture(unittest.TestCase):
    """Shared representative weekly data for report builder tests."""

    METRICS = {
        "ga4": {
            "period": {"start": "2026-08-19", "end": "2026-08-25"},
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
        },
        "meta_ads": {
            "period": {"start": "2026-08-19", "end": "2026-08-25"},
            "totals": {"spend": 1240.50, "impressions": 85000, "clicks": 1020, "ctr": 1.2},
            "campaigns": [
                {
                    "name": "Brand Awareness Q3",
                    "spend": 720.00,
                    "impressions": 50000,
                    "clicks": 600,
                    "ctr": 1.2,
                    "roas": 3.4,
                }
            ],
        },
        "linkedin_ads": {
            "period": {"start": "2026-08-19", "end": "2026-08-25"},
            "totals": {
                "spend": 680.00,
                "impressions": 22000,
                "clicks": 310,
                "ctr": 1.4091,
                "landing_page_clicks": 240,
                "conversions": 18,
            },
            "campaigns": [
                {
                    "id": "123",
                    "name": "Lead Generation Q3",
                    "spend": 680.00,
                    "impressions": 22000,
                    "clicks": 310,
                    "ctr": 1.4091,
                    "landing_page_clicks": 240,
                    "conversions": 18,
                }
            ],
        },
    }

    @staticmethod
    def client():
        sys.modules.pop("scripts.report_builder", None)
        from scripts import report_builder
        return report_builder


class TestReportInputValidation(ReportBuilderFixture):
    """Validate the structured input contract."""

    def test_missing_required_source_raises(self):
        client = self.client()
        invalid = {"ga4": {}, "meta_ads": {}}
        with self.assertRaises(ValueError):
            client.validate_metrics(invalid)

    def test_source_must_be_object(self):
        client = self.client()
        invalid = {**self.METRICS, "meta_ads": []}
        with self.assertRaises(ValueError):
            client.validate_metrics(invalid)

    def test_build_analysis_input_limits_long_lists(self):
        client = self.client()
        metrics = json.loads(json.dumps(self.METRICS))
        metrics["ga4"]["top_pages"] = [{"page": f"/{index}", "sessions": index} for index in range(10)]
        payload = client.build_analysis_input(metrics)
        self.assertEqual(len(payload["website"]["top_pages"]), 5)
        self.assertIn("report_period", payload)

    def test_load_metrics_rejects_invalid_json(self):
        client = self.client()
        with tempfile.TemporaryDirectory() as directory:
            invalid_path = Path(directory) / "invalid.json"
            invalid_path.write_text("this is not JSON", encoding="utf-8")
            with self.assertRaises(ValueError):
                client.load_metrics(invalid_path)


class TestOpenAIAnalysis(ReportBuilderFixture):
    """Verify the OpenAI request and response handling without network calls."""

    def test_generate_analysis_uses_expected_payload(self):
        client = self.client()
        response = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"content": "## Executive summary\nStrong week."}}]
        }
        response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("requests.post", return_value=response) as post:
                analysis = client.generate_analysis(self.METRICS)

        self.assertEqual(analysis, "## Executive summary\nStrong week.")
        self.assertTrue(post.call_args.args[0].endswith("/chat/completions"))
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("Weekly marketing data", payload["messages"][1]["content"])

    def test_missing_openai_key_raises(self):
        client = self.client()
        environment = {key: value for key, value in os.environ.items() if key != "OPENAI_API_KEY"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(EnvironmentError):
                client.generate_analysis(self.METRICS)

    def test_empty_openai_content_raises(self):
        client = self.client()
        response = MagicMock()
        response.json.return_value = {"choices": [{"message": {"content": ""}}]}
        response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("requests.post", return_value=response):
                with self.assertRaises(ValueError):
                    client.generate_analysis(self.METRICS)


class TestPDFRenderer(ReportBuilderFixture):
    """Verify the generated PDF is a non-empty, valid PDF document."""

    ANALYSIS = """## Executive summary
Website traffic and paid activity generated measurable engagement this week.

## Key wins
- GA4 recorded 4,821 sessions.
- Meta Ads generated 1,020 clicks.

## Watchouts
- Compare the current period with the previous week before drawing trend conclusions.

## Recommended actions
1. Review conversion paths for the highest-traffic pages.
2. Shift a test budget to the highest-intent campaign.
3. Review LinkedIn lead quality with sales.
"""

    def test_render_pdf_creates_non_empty_file(self):
        client = self.client()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "weekly-marketing-report.pdf"
            result = client.render_pdf(self.METRICS, self.ANALYSIS, output)

            self.assertEqual(result, output)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1000)
            self.assertEqual(output.read_bytes()[:4], b"%PDF")

    def test_markdown_sections_are_parsed(self):
        client = self.client()
        sections = client._analysis_sections(self.ANALYSIS)
        titles = [title for title, _ in sections]
        self.assertEqual(titles, ["Executive summary", "Key wins", "Watchouts", "Recommended actions"])


if __name__ == "__main__":
    unittest.main()
