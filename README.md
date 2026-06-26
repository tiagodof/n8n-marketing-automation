# n8n Marketing Automation Suite

![Status](https://img.shields.io/badge/status-building-brightgreen)
![Module](https://img.shields.io/badge/module-01%20Reporting%20Agent-blue)
![n8n](https://img.shields.io/badge/n8n-automation-red)
![GPT-4](https://img.shields.io/badge/OpenAI-GPT--4-412991)
![License](https://img.shields.io/badge/license-MIT-green)

> **Build in public.** An open-source AI-powered marketing automation suite built with n8n, GPT-4 and real business integrations. Build started: 26 June 2026.

---

## Why this project exists

After more than a decade working in marketing, I spent countless hours on tasks that should have been automated: pulling weekly reports from three different ad platforms, monitoring competitors, briefing content teams, and manually enriching CRM leads.

The positive feedback I received on [FirstStep](https://firststep-nine.vercel.app) motivated me to go further. This project is the result.

This is not a tutorial. It is a real, working suite of automation workflows built in public, step by step.

---

## Modules

| # | Module | Description | Status |
|---|---|---|---|
| 01 | **AI Marketing Reporting Agent** | Pulls data from GA4, Meta Ads and LinkedIn Ads every Monday. GPT-4 analyses trends and generates an executive PDF report sent by email | 🔨 **In progress** |
| 02 | Competitor Intelligence Monitor | Monitors competitor mentions across Reddit, Google News and RSS feeds. AI filters noise and sends a daily digest to Slack | Planned |
| 03 | Social Media Content Calendar Generator | Takes a campaign brief and generates a 30-day content calendar for LinkedIn, Instagram and X | Planned |
| 04 | CRM Enrichment Pipeline | Enriches new HubSpot/Pipedrive contacts with company data and a GPT-4 priority score | Planned |

---

## Project structure

```
n8n-marketing-automation/
├── modules/
│   ├── 01-reporting-agent/
│   │   ├── workflows/      # n8n workflow JSON exports
│   │   ├── scripts/        # Python helper scripts (GA4, Meta, LinkedIn API)
│   │   ├── templates/      # Email and PDF report templates
│   │   └── tests/          # Unit tests
│   ├── 02-competitor-monitor/
│   ├── 03-content-calendar/
│   └── 04-crm-enrichment/
├── docker/                 # docker-compose for self-hosted n8n
└── docs/                   # Architecture diagrams and setup guides
```

---

## Tech stack

| Tool | Purpose |
|---|---|
| n8n (self-hosted via Docker) | Workflow orchestration |
| OpenAI GPT-4 | AI reasoning, content generation and scoring |
| Google Analytics 4 API | Website and campaign performance data |
| Meta Marketing API | Facebook and Instagram Ads data |
| LinkedIn API | LinkedIn Ads and organic data |
| SerpAPI | Competitor and company research |
| HubSpot / Pipedrive | CRM integration |
| Notion / Google Sheets | Data output and content calendars |
| Slack | Team notifications and digests |

---

## Build timeline

```
June 2026      ✅ Repository setup
               🔨 Module 01: AI Marketing Reporting Agent
July 2026      Module 02: Competitor Intelligence Monitor
               Module 03: Social Media Content Calendar Generator
August 2026    Module 04: CRM Enrichment Pipeline
September 2026 v1.0 release, full documentation and setup guide
```

---

## Follow the build

Every step of this project is shared publicly:

- **GitHub:** Each commit represents a real development step
- **LinkedIn:** Progress updates, decisions and lessons learned — [follow here](https://www.linkedin.com/in/tiago-oliveira-30359311a/)

If you work in marketing and have ever spent hours on manual reports or competitor research, this project is for you.

---

## License

MIT License. Free to use, fork and adapt.
