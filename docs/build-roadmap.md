# Build Roadmap

This document tracks the development progress of the n8n Marketing Automation Suite. Updates are pushed as development progresses. There is no fixed day per step: each piece ships when it is ready.

## Module 01: AI Marketing Reporting Agent

| Step | Date / window | What gets built |
|---|---|---|
| 1 | 26 Jun 2026 | Project structure, docker-compose, Makefile for local development, and architecture documentation. |
| 2 | 4 Jul 2026 | GA4 Python client that fetches sessions, conversions, top pages, and traffic sources. |
| 3 | 8 Aug 2026 | Meta Ads Python client that fetches spend, impressions, clicks, and ROAS by campaign. |
| 4 | 19 Aug 2026 | LinkedIn Ads Python client that fetches campaign spend, impressions, clicks, CTR, landing-page clicks, and conversions. |
| 5 | **26 Aug 2026** | AI analysis prompt, validated OpenAI response handling, PDF report renderer, sample metrics input, and automated tests. |
| 6 | Aug / Sep 2026 | n8n workflow that orchestrates all sources and sends the PDF by SMTP email. Module 01 complete. |

## Module 02: Competitor Intelligence Monitor

| Step | Window | What gets built |
|---|---|---|
| 7 | Aug / Sep 2026 | Reddit and RSS feed clients plus competitor keyword configuration. |
| 8 | Sep 2026 | AI noise filtering, Slack digest formatter, and n8n workflow. Module 02 complete. |

## Module 03: Social Media Content Calendar Generator

| Step | Window | What gets built |
|---|---|---|
| 9 | Sep 2026 | Campaign brief parser, AI calendar generator, and Notion and Google Sheets output. Module 03 complete. |

## Module 04: CRM Enrichment Pipeline

| Step | Window | What gets built |
|---|---|---|
| 10 | Sep / Oct 2026 | HubSpot/Pipedrive webhook listener, company data enrichment, and AI priority scoring. Module 04 complete. |

## v1.0 Release

| Step | Window | What gets built |
|---|---|---|
| 11 | Oct 2026 | Full setup guide, CHANGELOG, and v1.0 release tag. |
