"""AI report builder for Module 01: AI Marketing Reporting Agent.

The builder consumes normalised output from the GA4, Meta Ads, and LinkedIn Ads
clients. It requests an executive analysis from OpenAI and renders a compact PDF
for weekly stakeholder reporting.

Usage:
    python3 report_builder.py --input weekly_metrics.json --output reports/weekly-report.pdf

Required environment variables:
    OPENAI_API_KEY      OpenAI API key used for the executive analysis.

Optional environment variables:
    OPENAI_MODEL        Chat Completions model name. Defaults to gpt-4o.
    OPENAI_API_BASE     Base URL for OpenAI-compatible APIs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import requests
from fpdf import FPDF


OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """You are a senior performance marketing analyst.
You receive a structured weekly marketing snapshot from web analytics, Meta Ads,
and LinkedIn Ads. Write a clear, evidence-based executive analysis.

Use exactly these Markdown sections:
## Executive summary
A concise paragraph of 3 to 5 sentences with the most relevant results.

## Key wins
Provide 2 or 3 specific, metric-backed bullet points.

## Watchouts
Provide 1 or 2 risks, data gaps, or underperforming areas. If no concern is
visible in the data, state that the dataset is insufficient to identify one.

## Recommended actions
Provide exactly 3 practical next steps for the coming week.

Do not invent benchmarks, previous-period comparisons, costs, conversion value,
or campaign results that are missing from the supplied data. Use a professional,
direct tone and include exact values where relevant."""


def _number(value: Any) -> float:
    """Convert an arbitrary numeric API value to a safe float."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _integer(value: Any) -> int:
    """Convert an arbitrary numeric API value to a safe integer."""
    return int(_number(value))


def _clean_pdf_text(value: Any) -> str:
    """Convert text to a Helvetica-compatible representation for fpdf2."""
    text = str(value or "")
    substitutions = {
        "•": "-",
        "→": "->",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "€": "EUR ",
    }
    for source, replacement in substitutions.items():
        text = text.replace(source, replacement)
    return text.encode("latin-1", "replace").decode("latin-1")


def _format_number(value: Any) -> str:
    """Format a numeric metric for the PDF."""
    return f"{_integer(value):,}"


def _format_currency(value: Any) -> str:
    """Format a local-currency spending metric without assuming the currency."""
    return f"{_number(value):,.2f}"


def validate_metrics(metrics: Mapping[str, Any]) -> None:
    """Validate the top-level weekly data contract before analysis or rendering."""
    required = ("ga4", "meta_ads", "linkedin_ads")
    missing = [key for key in required if key not in metrics]
    if missing:
        raise ValueError(
            "The weekly metrics input is missing required section(s): "
            + ", ".join(missing)
            + "."
        )

    for key in required:
        if not isinstance(metrics[key], Mapping):
            raise ValueError(f"The '{key}' section must be a JSON object.")


def build_analysis_input(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Create a compact, stable payload for the AI analysis request."""
    validate_metrics(metrics)
    ga4 = metrics["ga4"]
    meta_ads = metrics["meta_ads"]
    linkedin_ads = metrics["linkedin_ads"]

    return {
        "report_period": ga4.get("period") or meta_ads.get("period") or linkedin_ads.get("period") or {},
        "website": {
            "overview": ga4.get("overview", {}),
            "top_pages": list(ga4.get("top_pages", []))[:5],
            "traffic_sources": list(ga4.get("traffic_sources", []))[:5],
        },
        "meta_ads": {
            "totals": meta_ads.get("totals", {}),
            "top_campaigns": list(meta_ads.get("campaigns", []))[:5],
        },
        "linkedin_ads": {
            "totals": linkedin_ads.get("totals", {}),
            "top_campaigns": list(linkedin_ads.get("campaigns", []))[:5],
        },
    }


def build_user_prompt(metrics: Mapping[str, Any]) -> str:
    """Format normalised data as the user message for the analysis model."""
    analysis_input = build_analysis_input(metrics)
    return "Weekly marketing data:\n\n" + json.dumps(analysis_input, indent=2, ensure_ascii=False)


def generate_analysis(metrics: Mapping[str, Any]) -> str:
    """Request an executive analysis from the configured OpenAI-compatible API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. See .env.example for setup instructions."
        )

    model = os.environ.get("OPENAI_MODEL", OPENAI_MODEL)
    api_base = os.environ.get("OPENAI_API_BASE", OPENAI_API_BASE).rstrip("/")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(metrics)},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }

    response = requests.post(
        f"{api_base}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()

    try:
        content = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as error:
        raise ValueError("The OpenAI response did not contain analysis content.") from error

    if not content:
        raise ValueError("The OpenAI response contained an empty analysis.")
    return content


class MarketingReportPDF(FPDF):
    """Minimal, readable PDF layout for the weekly executive report."""

    def header(self) -> None:
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(19, 43, 73)
        self.cell(0, 9, "Weekly Marketing Report", ln=1)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(90, 101, 115)
        self.cell(
            0,
            5,
            f"Generated {date.today().isoformat()} by n8n Marketing Automation Suite",
            ln=1,
        )
        self.ln(3)
        self.set_draw_color(203, 213, 225)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")

    def section(self, title: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 64, 175)
        self.multi_cell(0, 6, _clean_pdf_text(title))
        self.set_draw_color(191, 219, 254)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def paragraph(self, content: str) -> None:
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 41, 59)
        self.multi_cell(0, 5, _clean_pdf_text(content))
        self.ln(1)

    def metric_row(self, label: str, value: str) -> None:
        self.set_font("Helvetica", "", 9)
        self.set_text_color(71, 85, 105)
        self.cell(78, 5.5, _clean_pdf_text(label))
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(15, 23, 42)
        self.cell(0, 5.5, _clean_pdf_text(value), ln=1)


def _analysis_sections(analysis: str) -> list[tuple[str, str]]:
    """Split a Markdown analysis into PDF-friendly sections."""
    heading_pattern = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading_pattern.finditer(analysis.strip()))
    if not matches:
        return [("AI analysis", analysis.strip())]

    sections: list[tuple[str, str]] = []
    preface = analysis[: matches[0].start()].strip()
    if preface:
        sections.append(("AI analysis", preface))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(analysis)
        content = analysis[match.end() : end].strip()
        if content:
            sections.append((match.group(1), content))
    return sections


def _campaign_rows(campaigns: list[Mapping[str, Any]], max_rows: int = 5) -> list[tuple[str, str]]:
    """Prepare the top campaign metric rows for the PDF."""
    rows: list[tuple[str, str]] = []
    for campaign in campaigns[:max_rows]:
        name = str(campaign.get("name", "Unknown campaign"))
        spend = _format_currency(campaign.get("spend"))
        clicks = _format_number(campaign.get("clicks"))
        ctr = _number(campaign.get("ctr"))
        rows.append((name, f"Spend {spend} | Clicks {clicks} | CTR {ctr:.2f}%"))
    return rows


def render_pdf(metrics: Mapping[str, Any], analysis: str, output_path: str | Path) -> Path:
    """Render the executive analysis and core metrics as a PDF report."""
    validate_metrics(metrics)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    ga4 = metrics["ga4"]
    meta_ads = metrics["meta_ads"]
    linkedin_ads = metrics["linkedin_ads"]
    period = ga4.get("period") or meta_ads.get("period") or linkedin_ads.get("period") or {}

    pdf = MarketingReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    start = period.get("start", "not provided")
    end = period.get("end", "not provided")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, _clean_pdf_text(f"Reporting period: {start} to {end}"), ln=1)

    for title, content in _analysis_sections(analysis):
        pdf.section(title)
        pdf.paragraph(content)

    overview = ga4.get("overview", {})
    pdf.section("Website performance: Google Analytics 4")
    pdf.metric_row("Sessions", _format_number(overview.get("sessions")))
    pdf.metric_row("Users", _format_number(overview.get("users")))
    pdf.metric_row("New users", _format_number(overview.get("new_users")))
    pdf.metric_row("Conversions", _format_number(overview.get("conversions")))
    pdf.metric_row("Bounce rate", f"{_number(overview.get('bounce_rate')):.2f}%")

    meta_totals = meta_ads.get("totals", {})
    pdf.section("Paid social: Meta Ads")
    pdf.metric_row("Spend", _format_currency(meta_totals.get("spend")))
    pdf.metric_row("Impressions", _format_number(meta_totals.get("impressions")))
    pdf.metric_row("Clicks", _format_number(meta_totals.get("clicks")))
    pdf.metric_row("CTR", f"{_number(meta_totals.get('ctr')):.2f}%")
    for name, value in _campaign_rows(list(meta_ads.get("campaigns", []))):
        pdf.metric_row(f"Campaign: {name}", value)

    linkedin_totals = linkedin_ads.get("totals", {})
    pdf.section("Paid social: LinkedIn Ads")
    pdf.metric_row("Spend", _format_currency(linkedin_totals.get("spend")))
    pdf.metric_row("Impressions", _format_number(linkedin_totals.get("impressions")))
    pdf.metric_row("Clicks", _format_number(linkedin_totals.get("clicks")))
    pdf.metric_row("CTR", f"{_number(linkedin_totals.get('ctr')):.2f}%")
    for name, value in _campaign_rows(list(linkedin_ads.get("campaigns", []))):
        pdf.metric_row(f"Campaign: {name}", value)

    pdf.output(str(output))
    return output


def load_metrics(input_path: str | Path) -> dict[str, Any]:
    """Load and validate weekly metrics from a JSON file."""
    path = Path(input_path)
    try:
        metrics = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Metrics input file was not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Metrics input file is not valid JSON: {path}") from error

    if not isinstance(metrics, dict):
        raise ValueError("Metrics input must be a top-level JSON object.")
    validate_metrics(metrics)
    return metrics


def build_report(input_path: str | Path, output_path: str | Path) -> Path:
    """Run the complete weekly reporting pipeline and return the PDF path."""
    metrics = load_metrics(input_path)
    analysis = generate_analysis(metrics)
    return render_pdf(metrics, analysis, output_path)


def main() -> None:
    """Run the report builder command-line interface."""
    parser = argparse.ArgumentParser(description="Build an AI marketing PDF report.")
    parser.add_argument("--input", required=True, help="Path to the merged weekly metrics JSON file.")
    parser.add_argument("--output", required=True, help="Destination path for the generated PDF.")
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the prepared OpenAI user prompt without calling the API or creating a PDF.",
    )
    args = parser.parse_args()

    metrics = load_metrics(args.input)
    if args.print_prompt:
        print(build_user_prompt(metrics))
        return

    report_path = build_report(args.input, args.output)
    print(json.dumps({"report_path": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
