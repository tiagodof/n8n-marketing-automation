# Module 01 — AI Marketing Reporting Agent

## What it does

Every Monday morning this module:

1. Pulls the last 7 days of data from **Google Analytics 4**, **Meta Ads** and **LinkedIn Ads**
2. Sends the raw metrics to **GPT-4**, which writes a concise executive summary with trend analysis and actionable recommendations
3. Renders the summary into a clean **PDF report**
4. Delivers the report by **email** to the configured recipient(s)

## Architecture

```
[n8n Cron — Monday 07:00]
        |
        ├── [GA4 Script]        → sessions, conversions, top pages, traffic sources
        ├── [Meta Ads Script]   → spend, impressions, clicks, CTR, ROAS by campaign
        └── [LinkedIn Ads Script] → impressions, clicks, CTR, spend by campaign
        |
        ↓
[Merge & normalise data]
        |
        ↓
[GPT-4 — generate executive summary]
        |
        ↓
[PDF renderer]
        |
        ↓
[Send email via SMTP]
```

## Files

| File | Purpose |
|---|---|
| `workflows/reporting_agent.json` | n8n workflow export — import directly into your n8n instance |
| `scripts/ga4_client.py` | Fetches GA4 data via the Google Analytics Data API |
| `scripts/meta_ads_client.py` | Fetches Meta Ads data via the Marketing API |
| `scripts/linkedin_ads_client.py` | Fetches LinkedIn Ads data via the Marketing API |
| `scripts/report_builder.py` | Merges data, calls GPT-4, renders PDF |
| `templates/report_email.html` | HTML email template |
| `tests/test_ga4_client.py` | Unit tests for GA4 client |

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials
2. Start n8n: `cd docker && docker-compose up -d`
3. Open n8n at `http://localhost:5678`
4. Import `workflows/reporting_agent.json`
5. Activate the workflow

## Required credentials

- Google Cloud service account with **Google Analytics Data API** enabled
- Meta App with **ads_read** permission and a long-lived access token
- LinkedIn App with **r_ads_reporting** scope
- OpenAI API key
- SMTP credentials for email delivery
