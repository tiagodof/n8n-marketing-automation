# n8n Marketing Automation Suite

![Status](https://img.shields.io/badge/status-building-brightgreen)
![Module 01](https://img.shields.io/badge/module--01-complete-2563eb)
![n8n](https://img.shields.io/badge/n8n-automation-red)
![OpenAI](https://img.shields.io/badge/OpenAI-AI%20analysis-412991)
![License](https://img.shields.io/badge/license-MIT-green)

> **Build in public.** An open-source marketing automation suite that combines n8n, Python, AI analysis, and real business integrations. Development started in June 2026.

## Why this project exists

After more than a decade in marketing, I spent countless hours on work that should be automated: exporting reports from ad platforms, reviewing performance, monitoring competitors, briefing content teams, and enriching CRM leads.

The positive feedback I received on [FirstStep](https://firststep-nine.vercel.app) motivated me to build a practical solution. This is not a tutorial. It is a working suite of automation workflows, developed in public as real product components.

## Modules

| # | Module | Description | Status |
|---|---|---|---|
| 01 | **AI Marketing Reporting Agent** | Collects GA4, Meta Ads, and LinkedIn Ads data, generates an AI executive analysis and PDF report, and sends it by email. | **Complete** |
| 02 | Competitor Intelligence Monitor | Monitors competitor mentions across Reddit, Google News, and RSS feeds. AI filters noise and prepares a daily Slack digest. | Planned |
| 03 | Social Media Content Calendar Generator | Converts a campaign brief into a 30-day content calendar for LinkedIn, Instagram, and X. | Planned |
| 04 | CRM Enrichment Pipeline | Enriches new HubSpot or Pipedrive contacts with company data and an AI priority score. | Planned |

## Module 01: AI Marketing Reporting Agent

Module 01 is the first complete workflow in the suite. n8n schedules the weekly run or starts it manually, then calls a private reporting service over the internal Docker network. The service holds the GA4, Meta, LinkedIn, and OpenAI credentials, creates the PDF, and returns its metadata. n8n loads the PDF from a read-only shared volume and sends it with the configured SMTP account.

```text
n8n trigger -> private reporting service -> GA4 / Meta / LinkedIn / OpenAI
     |                                                   |
     +-------------- shared report volume <--------------+
                              |
                              v
                    SMTP email with PDF attachment
```

The reporting service has no public port. See the [Module 01 guide](modules/01-reporting-agent/README.md) for installation, security controls, credential setup, and test commands.

## Project structure

```text
n8n-marketing-automation/
├── modules/
│   ├── 01-reporting-agent/
│   │   ├── examples/       # Sample normalised marketing metrics
│   │   ├── scripts/        # Data clients and report pipeline
│   │   ├── service/        # Private reporting API
│   │   ├── templates/      # HTML email template
│   │   ├── tests/          # Unit and workflow tests
│   │   └── workflows/      # Importable n8n workflow JSON
│   ├── 02-competitor-monitor/
│   ├── 03-content-calendar/
│   └── 04-crm-enrichment/
├── docker/                 # Docker Compose and service image
├── reports/                # Shared local report directory
└── docs/                   # Architecture and technical roadmap
```

## Tech stack

| Technology | Purpose |
|---|---|
| n8n, self-hosted with Docker | Workflow orchestration, schedules, and email delivery |
| FastAPI | Private reporting service that n8n calls inside the Docker network |
| Python | Marketing API clients, data normalisation, AI analysis, and PDF generation |
| OpenAI API | Evidence-based executive analysis and recommended actions |
| Google Analytics 4 Data API | Website sessions, conversions, top pages, and traffic sources |
| Meta Marketing API | Campaign spend, impressions, clicks, CTR, and ROAS |
| LinkedIn Marketing API | Campaign-level paid-media performance |
| SMTP | Delivery of the weekly PDF report |

## Getting started

Copy the environment example, enter your API credentials, choose a long random value for `REPORTING_SERVICE_TOKEN`, and start the local stack:

```bash
cp .env.example .env
make start
```

Open n8n at `http://localhost:5678`, import `modules/01-reporting-agent/workflows/reporting_agent.json`, configure the SMTP credential in the **Email report** node, run the workflow manually, and publish it after you verify the email delivery.

The Module 01 test suite can be run with:

```bash
make test
```

## Roadmap

The technical project roadmap is available in [docs/build-roadmap.md](docs/build-roadmap.md). Module 02, the Competitor Intelligence Monitor, is the next development stage.

## Follow the build

Each commit represents a real development step. Progress updates, decisions, and lessons learned are shared through [LinkedIn](https://www.linkedin.com/in/tiago-oliveira-30359311a/) and this repository.

## License

MIT License. Free to use, fork, and adapt.
