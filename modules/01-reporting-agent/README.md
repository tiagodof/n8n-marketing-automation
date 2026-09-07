# Module 01: AI Marketing Reporting Agent

## What it does

This module produces a weekly executive marketing report from **Google Analytics 4**, **Meta Ads**, and **LinkedIn Ads**. The reporting service collects the normalised source data, asks OpenAI to write an executive analysis, creates a PDF, and returns the report metadata to n8n. The n8n workflow attaches the PDF to an HTML email and sends it through SMTP.

The service runs privately inside the Docker network. It is not exposed to the host machine or the public internet. n8n accesses it through a protected internal HTTP request.

## Architecture

```text
n8n schedule or manual trigger
             |
             v
private reporting service
   | GA4, Meta Ads, LinkedIn Ads
   | OpenAI executive analysis
   | PDF generation
             |
             v
shared reports volume
             |
             v
n8n SMTP email with PDF attachment
```

## Components

| Component | Responsibility |
|---|---|
| `scripts/ga4_client.py` | Retrieves website sessions, users, conversions, top pages, and traffic sources from the GA4 Data API. |
| `scripts/meta_ads_client.py` | Retrieves Meta Ads spend, impressions, clicks, CTR, ROAS, and campaign-level results. |
| `scripts/linkedin_ads_client.py` | Retrieves campaign-level LinkedIn Ads performance. |
| `scripts/report_builder.py` | Validates the merged metrics, gets an AI executive analysis, and creates the PDF report. |
| `scripts/run_reporting_pipeline.py` | Runs the complete collection and reporting pipeline. |
| `service/app.py` | Private FastAPI service called by n8n over the Docker network. |
| `workflows/reporting_agent.json` | Importable n8n workflow for a weekly schedule, manual test, PDF attachment, and SMTP delivery. |
| `templates/report_email.html` | Responsive HTML email body returned by the reporting service. |
| `examples/weekly_metrics.example.json` | Sample input for inspecting the analysis contract without live platform credentials. |

## Local setup

Copy the root environment example and add real credentials. `REPORTING_SERVICE_TOKEN` should be a random secret with at least 32 characters. It is shared only between n8n and the reporting service.

```bash
cp .env.example .env
```

Start the stack from the repository root:

```bash
make start
```

The `reporting-service` is intentionally internal-only. Open n8n at `http://localhost:5678`, import `workflows/reporting_agent.json`, and configure an SMTP credential in the **Email report** node. The workflow uses `SMTP_USER` as the sender and `REPORT_RECIPIENT_EMAIL` as the recipient.

Use the **Run manually** trigger first. Confirm that the PDF arrives as an attachment before publishing the workflow. Scheduled workflows must be saved and published before the scheduler runs.[1]

## Security model

| Area | Design decision |
|---|---|
| Reporting APIs | GA4, Meta Ads, LinkedIn Ads, and OpenAI credentials are available only to `reporting-service`. |
| Service access | The private API requires `Authorization: Bearer <REPORTING_SERVICE_TOKEN>`. |
| File handling | Reports are written to a shared Docker volume. n8n mounts this volume as read-only. |
| Workflow scope | n8n uses the HTTP Request, Read/Write Files, and Email nodes. It does not need command execution. |
| SMTP configuration | The credential is created in the n8n editor and remains outside version control. |

## Validate before adding credentials

Inspect the exact metrics passed to the AI layer without making network calls:

```bash
python3 modules/01-reporting-agent/scripts/report_builder.py \
  --input modules/01-reporting-agent/examples/weekly_metrics.example.json \
  --output /tmp/weekly-marketing-report.pdf \
  --print-prompt
```

Run the full test suite with:

```bash
python3 -m unittest discover \
  -s modules/01-reporting-agent/tests \
  -p 'test_*.py' \
  -v
```

## Current scope

The Module 01 code path is complete: source collection, AI analysis, PDF rendering, internal orchestration, and SMTP workflow delivery are all represented in the repository. A live run requires the user to provide the required platform credentials and an SMTP credential in n8n.

## References

[1]: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/ "n8n: Schedule Trigger"
[2]: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.sendemail/ "n8n: Send Email"
[3]: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile/ "n8n: Read/Write Files from Disk"
