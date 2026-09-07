"""Run the complete Module 01 reporting pipeline.

This entry point is designed for the n8n Execute Command node in the self-hosted
container. It collects data from GA4, Meta Ads, and LinkedIn Ads, creates the
AI analysis and PDF report, then prints machine-readable JSON to standard output.

Usage:
    python3 run_reporting_pipeline.py --days 7 --output-dir /home/node/project/reports
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from . import ga4_client, linkedin_ads_client, meta_ads_client, report_builder
except ImportError:
    import ga4_client  # type: ignore[no-redef]
    import linkedin_ads_client  # type: ignore[no-redef]
    import meta_ads_client  # type: ignore[no-redef]
    import report_builder  # type: ignore[no-redef]


DEFAULT_DAYS = 7
DEFAULT_OUTPUT_DIR = "/home/node/project/reports"
EMAIL_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "report_email.html"


def render_email_html(report_period_start: str, report_period_end: str) -> str:
    """Render the weekly email template with report-period placeholders."""
    try:
        template = EMAIL_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Email template was not found: {EMAIL_TEMPLATE_PATH}"
        ) from error

    return (
        template.replace("{{report_period_start}}", report_period_start)
        .replace("{{report_period_end}}", report_period_end)
    )


def collect_weekly_metrics(days: int = DEFAULT_DAYS) -> dict[str, Any]:
    """Collect normalised weekly data from every reporting source."""
    if days < 1:
        raise ValueError("days must be at least 1.")

    return {
        "ga4": ga4_client.fetch_weekly_summary(days=days),
        "meta_ads": meta_ads_client.fetch_weekly_summary(days=days),
        "linkedin_ads": linkedin_ads_client.fetch_weekly_summary(days=days),
    }


def _report_filename(metrics: dict[str, Any]) -> str:
    """Build a stable report filename from the completed reporting period."""
    period = metrics.get("ga4", {}).get("period", {})
    end_date = str(period.get("end", "weekly"))
    return f"weekly-marketing-report-{end_date}.pdf"


def run_pipeline(
    days: int = DEFAULT_DAYS,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """Collect metrics, render a report, and return paths for n8n to consume."""
    metrics = collect_weekly_metrics(days=days)
    selected_output_dir = output_dir or os.environ.get(
        "REPORT_OUTPUT_DIR", DEFAULT_OUTPUT_DIR
    )
    output_path = Path(selected_output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metrics_path = output_path / "weekly-marketing-metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    report_path = output_path / _report_filename(metrics)
    analysis = report_builder.generate_analysis(metrics)
    report_builder.render_pdf(metrics, analysis, report_path)

    report_period = metrics["ga4"]["period"]
    report_period_start = str(report_period["start"])
    report_period_end = str(report_period["end"])

    return {
        "report_path": str(report_path),
        "report_filename": report_path.name,
        "metrics_path": str(metrics_path),
        "report_period_start": report_period_start,
        "report_period_end": report_period_end,
        "email_html": render_email_html(report_period_start, report_period_end),
    }


def main() -> None:
    """Run the command-line interface and print JSON for the n8n workflow."""
    parser = argparse.ArgumentParser(description="Run the weekly marketing reporting pipeline.")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Number of completed days to include in the report.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("REPORT_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        help="Directory where the PDF and normalised metrics JSON will be written.",
    )
    args = parser.parse_args()

    result = run_pipeline(days=args.days, output_dir=args.output_dir)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
