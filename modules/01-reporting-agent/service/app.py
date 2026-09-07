"""Private HTTP service for the AI Marketing Reporting Agent.

This service has no public port mapping. The n8n workflow calls it across the
internal Docker network to generate a weekly PDF report. The returned report path
is shared with n8n through the reports volume.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_reporting_pipeline  # noqa: E402


class WeeklyReportRequest(BaseModel):
    """Input accepted from the internal n8n workflow."""

    days: int = Field(default=7, ge=1, le=31)


class WeeklyReportResponse(BaseModel):
    """Metadata that n8n needs to attach and email the generated report."""

    report_path: str
    report_filename: str
    metrics_path: str
    report_period_start: str
    report_period_end: str
    email_html: str


app = FastAPI(
    title="AI Marketing Reporting Service",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


def _verify_internal_token(authorization: str | None) -> None:
    """Require a shared bearer token for all report-generation requests."""
    expected_token = os.environ.get("REPORTING_SERVICE_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reporting service token is not configured.",
        )

    received_token = authorization.removeprefix("Bearer ") if authorization else ""
    if not secrets.compare_digest(received_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reporting service token.",
        )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Expose a lightweight healthcheck for Docker without revealing credentials."""
    return {"status": "ok"}


@app.post("/v1/reports/weekly", response_model=WeeklyReportResponse)
def create_weekly_report(
    request: WeeklyReportRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Generate a weekly report and return its metadata for the n8n email step."""
    _verify_internal_token(authorization)

    try:
        result = run_reporting_pipeline.run_pipeline(days=request.days)
    except (EnvironmentError, FileNotFoundError, ImportError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {error}",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report generation failed unexpectedly. Check the reporting service logs.",
        ) from error

    return result
