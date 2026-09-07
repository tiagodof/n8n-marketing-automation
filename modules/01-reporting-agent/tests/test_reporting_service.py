"""Tests for the private reporting service and its email hand-off data."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

MODULE_ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIR = MODULE_ROOT / "service"
SCRIPTS_DIR = MODULE_ROOT / "scripts"

for path in (str(SERVICE_DIR), str(SCRIPTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


class TestReportingPipelineHelpers(unittest.TestCase):
    """Validate deterministic pipeline helpers without calling external APIs."""

    @staticmethod
    def pipeline_module():
        sys.modules.pop("run_reporting_pipeline", None)
        return importlib.import_module("run_reporting_pipeline")

    def test_report_filename_uses_period_end(self):
        pipeline = self.pipeline_module()
        metrics = {"ga4": {"period": {"end": "2026-08-26"}}}
        self.assertEqual(
            pipeline._report_filename(metrics),
            "weekly-marketing-report-2026-08-26.pdf",
        )

    def test_email_template_includes_report_period(self):
        pipeline = self.pipeline_module()
        html = pipeline.render_email_html("2026-08-19", "2026-08-25")
        self.assertIn("2026-08-19", html)
        self.assertIn("2026-08-25", html)
        self.assertNotIn("{{report_period_start}}", html)
        self.assertNotIn("{{report_period_end}}", html)

    def test_pipeline_uses_environment_output_directory_when_not_overridden(self):
        pipeline = self.pipeline_module()
        metrics = {"ga4": {"period": {"start": "2026-08-19", "end": "2026-08-25"}}}

        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"REPORT_OUTPUT_DIR": directory}, clear=False):
                with patch.object(pipeline, "collect_weekly_metrics", return_value=metrics):
                    with patch.object(pipeline.report_builder, "generate_analysis", return_value="Analysis"):
                        with patch.object(pipeline.report_builder, "render_pdf") as render:
                            result = pipeline.run_pipeline()

            expected_report_path = Path(directory) / "weekly-marketing-report-2026-08-25.pdf"
            self.assertEqual(result["report_path"], str(expected_report_path))
            self.assertTrue((Path(directory) / "weekly-marketing-metrics.json").exists())
            render.assert_called_once_with(metrics, "Analysis", expected_report_path)


class TestReportingService(unittest.TestCase):
    """Verify health, authentication, and response behaviour of the private API."""

    @staticmethod
    def service_module():
        sys.modules.pop("app", None)
        return importlib.import_module("app")

    def test_healthcheck_is_public(self):
        service = self.service_module()
        response = TestClient(service.app).get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_missing_or_invalid_token_is_rejected(self):
        with patch.dict(os.environ, {"REPORTING_SERVICE_TOKEN": "expected-token"}, clear=False):
            service = self.service_module()
            client = TestClient(service.app)
            missing = client.post("/v1/reports/weekly", json={"days": 7})
            invalid = client.post(
                "/v1/reports/weekly",
                json={"days": 7},
                headers={"Authorization": "Bearer invalid-token"},
            )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)

    def test_report_request_returns_pipeline_result(self):
        expected = {
            "report_path": "/reports/weekly-marketing-report-2026-08-25.pdf",
            "report_filename": "weekly-marketing-report-2026-08-25.pdf",
            "metrics_path": "/reports/weekly-marketing-metrics.json",
            "report_period_start": "2026-08-19",
            "report_period_end": "2026-08-25",
            "email_html": "<html>Report</html>",
        }
        with patch.dict(os.environ, {"REPORTING_SERVICE_TOKEN": "expected-token"}, clear=False):
            service = self.service_module()
            with patch.object(service.run_reporting_pipeline, "run_pipeline", return_value=expected) as run:
                response = TestClient(service.app).post(
                    "/v1/reports/weekly",
                    json={"days": 14},
                    headers={"Authorization": "Bearer expected-token"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        run.assert_called_once_with(days=14)

    def test_days_outside_allowed_range_is_rejected(self):
        with patch.dict(os.environ, {"REPORTING_SERVICE_TOKEN": "expected-token"}, clear=False):
            service = self.service_module()
            response = TestClient(service.app).post(
                "/v1/reports/weekly",
                json={"days": 0},
                headers={"Authorization": "Bearer expected-token"},
            )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
