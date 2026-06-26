# Architecture Overview

## System design

The suite is built around a self-hosted **n8n** instance running in Docker. Each module is an independent n8n workflow that can be activated, paused and modified without affecting the others.

Python scripts handle all API calls and data processing. n8n orchestrates the execution order, manages credentials securely, and handles retries and error notifications.

```
┌─────────────────────────────────────────────────────────────────┐
│                        n8n (Docker)                             │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Module 01       │  │  Module 02       │  ...               │
│  │  Reporting Agent │  │  Competitor Mon. │                    │
│  └────────┬─────────┘  └──────────────────┘                    │
│           │                                                     │
│  ┌────────▼─────────────────────────────────────────────────┐  │
│  │  Python scripts (via Execute Command node)               │  │
│  │  ga4_client.py  │  meta_ads_client.py  │  report_builder  │  │
│  └────────┬─────────────────────────────────────────────────┘  │
└───────────┼─────────────────────────────────────────────────────┘
            │
            ├── Google Analytics 4 API
            ├── Meta Marketing API
            ├── LinkedIn Marketing API
            ├── OpenAI API (GPT-4)
            └── SMTP → Email delivery
```

## Module execution schedule

| Module | Trigger | Frequency |
|---|---|---|
| 01 — Reporting Agent | Cron `0 7 * * 1` | Every Monday at 07:00 |
| 02 — Competitor Monitor | Cron `0 8 * * *` | Every day at 08:00 |
| 03 — Content Calendar | Webhook (manual trigger) | On demand |
| 04 — CRM Enrichment | n8n Trigger (HubSpot/Pipedrive webhook) | On new contact |

## Data flow — Module 01

```
Cron trigger (Monday 07:00)
        │
        ├─ ga4_client.py      → GA4 Data API  → JSON
        ├─ meta_ads_client.py → Meta API      → JSON
        └─ linkedin_ads_client.py → LinkedIn API → JSON
                │
        Merge & parse in n8n Code node
                │
        GPT-4 (gpt-4o) → executive summary text
                │
        report_builder.py → PDF (fpdf2)
                │
        n8n Email Send → SMTP → recipient inbox
```

## Security

All credentials are stored as n8n environment variables and never committed to the repository. The `.env.example` file documents the required variables. The actual `.env` file is listed in `.gitignore`.
