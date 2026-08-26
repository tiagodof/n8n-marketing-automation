# Module 01: AI Marketing Reporting Agent

## What it does

This module prepares a weekly executive marketing report from three data sources: **Google Analytics 4**, **Meta Ads**, and **LinkedIn Ads**. The three connector scripts output a normalised JSON structure. `report_builder.py` then sends a compact version of that data to OpenAI, receives a structured executive analysis, and renders the analysis and core metrics into a PDF.

The final n8n workflow, scheduled for the next step, will orchestrate the sources and email the report every Monday.

## Current architecture

```text
GA4 client -----------\
Meta Ads client ------- > normalised weekly metrics JSON -> OpenAI analysis -> PDF report
LinkedIn Ads client ---/                                              |
                                                                       v
                                                         n8n email delivery (next step)
```

## Implemented files

| File | Responsibility |
|---|---|
| `scripts/ga4_client.py` | Retrieves website sessions, users, conversions, top pages, and traffic sources from the GA4 Data API. |
| `scripts/meta_ads_client.py` | Retrieves spend, impressions, clicks, CTR, ROAS, and campaign-level results from the Meta Marketing API. |
| `scripts/linkedin_ads_client.py` | Retrieves campaign-level LinkedIn Ads performance from the LinkedIn Reporting API. |
| `scripts/report_builder.py` | Validates the merged metrics, asks OpenAI for an executive analysis, and renders a PDF report. |
| `examples/weekly_metrics.example.json` | Example normalised input for local validation without live platform credentials. |
| `requirements.txt` | Python dependencies for the connector and PDF components. |
| `tests/` | Unit tests for data validation, API request construction, AI response handling, and PDF output. |

## Local setup

Install the module dependencies from the repository root:

```bash
pip install -r modules/01-reporting-agent/requirements.txt
```

Copy `.env.example` to `.env` and set the credentials required for the data sources you intend to run. `OPENAI_API_KEY` is required when generating a live analysis and PDF.

## Test the data contract without credentials

The example JSON allows you to inspect exactly what is sent for analysis without calling OpenAI:

```bash
python3 modules/01-reporting-agent/scripts/report_builder.py \
  --input modules/01-reporting-agent/examples/weekly_metrics.example.json \
  --output /tmp/weekly-marketing-report.pdf \
  --print-prompt
```

Run all module tests with:

```bash
python3 -m unittest discover \
  -s modules/01-reporting-agent/tests \
  -p 'test_*.py' \
  -v
```

## Generate a live report

Once the metrics JSON contains real output from the three connectors and `OPENAI_API_KEY` is configured, run:

```bash
python3 modules/01-reporting-agent/scripts/report_builder.py \
  --input path/to/weekly_metrics.json \
  --output reports/weekly-marketing-report.pdf
```

The generated PDF contains an AI executive summary, key wins, watchouts, recommended actions, core website metrics, and the top paid-campaign metrics.

## Required credentials

| Service | Required configuration |
|---|---|
| Google Analytics 4 | Service account JSON and a GA4 property ID. |
| Meta Ads | Long-lived token with `ads_read` and an ad account ID. |
| LinkedIn Ads | OAuth token with `r_ads_reporting` and a numeric ad account ID. |
| OpenAI | API key, plus optional model and compatible API base URL overrides. |
| SMTP | Required only in the next step, when n8n sends the finished report by email. |

## Current limitations

The PDF renderer is complete, but the n8n orchestration and email delivery are intentionally not included yet. They will be added in the final Module 01 workflow step.
