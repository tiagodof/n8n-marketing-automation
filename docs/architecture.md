# Architecture Overview

## System design

The suite uses a self-hosted n8n instance to coordinate its workflows. Module 01 separates orchestration from the workload that handles advertising and analytics credentials: n8n calls a private reporting service through the Docker network, and the service gathers data, requests the AI analysis, and renders the PDF.

This boundary keeps the application credentials for GA4, Meta Ads, LinkedIn Ads, and OpenAI inside the reporting service. The n8n container receives only the internal service token, the delivery address, and the shared report volume.

```text
                         Internal Docker network

+-------------------+        authenticated POST        +------------------------+
| n8n               | --------------------------------> | reporting-service      |
|                   |                                   |                        |
| Weekly schedule   |                                   | GA4 client             |
| Manual trigger    |                                   | Meta Ads client        |
| HTTP Request      |                                   | LinkedIn Ads client    |
+---------+---------+                                   | OpenAI analysis        |
          |                                             | PDF renderer           |
          |                                             +-----------+------------+
          |                                                         |
          |                          shared reports volume         |
          +-------------------------- read-only -------------------+
          |
          v
+-------------------+
| SMTP Email node   |
| attaches PDF      |
| sends report      |
+-------------------+
```

The reporting service does not expose a host port. It is reachable only by the n8n container at `http://reporting-service:8080`. Each report-generation request must include the `REPORTING_SERVICE_TOKEN` bearer token. The workflow is imported inactive and should be tested manually before it is published.

## Module 01 workflow

The importable workflow is stored at `modules/01-reporting-agent/workflows/reporting_agent.json`. It offers a manual trigger for validation and a weekly schedule for Monday at 07:00 in the `Europe/Lisbon` timezone. n8n requires schedule-trigger workflows to be saved and published before the schedule runs.[1]

| Node | Responsibility |
|---|---|
| `Weekly schedule` | Triggers the flow every Monday at 07:00. |
| `Run manually` | Allows a safe first run from the n8n editor. |
| `Generate weekly report` | Calls the internal reporting service with an authenticated HTTP request. |
| `Load report PDF` | Reads the generated file from the shared reports volume into the `report_pdf` binary field. |
| `Email report` | Sends the HTML summary and attaches the `report_pdf` file using the configured SMTP credential. |

## Module execution schedule

| Module | Trigger | Frequency |
|---|---|---|
| 01: Reporting Agent | n8n Schedule Trigger | Every Monday at 07:00 |
| 02: Competitor Monitor | Scheduled workflow | Planned |
| 03: Content Calendar | On-demand workflow | Planned |
| 04: CRM Enrichment | CRM webhook | Planned |

## Security controls

| Control | Implementation |
|---|---|
| Network isolation | `reporting-service` has no `ports` mapping and stays on the internal Docker network. |
| Service authentication | n8n sends the shared bearer token in `REPORTING_SERVICE_TOKEN`. |
| Least-privilege credentials | Platform and OpenAI credentials are mounted only into the reporting service. |
| File access | n8n has read-only access to `/reports` and is restricted to that path. |
| Email credentials | The SMTP credential is configured in n8n and is not committed to the repository. |
| Safe activation | The workflow is delivered with `active: false`; it must be manually tested and published. |

## References

[1]: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/ "n8n: Schedule Trigger"
[2]: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.sendemail/ "n8n: Send Email"
[3]: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile/ "n8n: Read/Write Files from Disk"
