"""
GA4 Client — Module 01: AI Marketing Reporting Agent
Fetches the last N days of data from Google Analytics 4 via the Data API.

Usage:
    python3 ga4_client.py
    python3 ga4_client.py --days 14

Required environment variables:
    GA4_PROPERTY_ID              — your GA4 property ID (numeric)
    GOOGLE_SERVICE_ACCOUNT_KEY   — service account JSON key (as a string)
"""

import os
import json
import argparse
from datetime import date, timedelta
from typing import Optional

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest, OrderBy,
    )
    from google.oauth2 import service_account
    GA4_AVAILABLE = True
except ImportError:
    GA4_AVAILABLE = False


def _get_client() -> "BetaAnalyticsDataClient":
    """Build an authenticated GA4 client from the service account key."""
    key_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not key_json:
        raise EnvironmentError(
            "GOOGLE_SERVICE_ACCOUNT_KEY is not set. "
            "See .env.example for setup instructions."
        )
    key_data = json.loads(key_json)
    credentials = service_account.Credentials.from_service_account_info(
        key_data,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def fetch_weekly_summary(
    property_id: Optional[str] = None,
    days: int = 7,
) -> dict:
    """
    Fetch a performance summary from GA4 for the last N days.

    Returns:
        {
            "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
            "overview": {
                "sessions": int,
                "users": int,
                "new_users": int,
                "conversions": int,
                "bounce_rate": float   # percentage, e.g. 42.3
            },
            "top_pages": [{"page": str, "sessions": int}, ...],
            "traffic_sources": [{"source": str, "medium": str, "sessions": int}, ...]
        }
    """
    pid = property_id or os.environ.get("GA4_PROPERTY_ID")
    if not pid:
        raise EnvironmentError(
            "GA4_PROPERTY_ID is not set. "
            "See .env.example for setup instructions."
        )

    if not GA4_AVAILABLE:
        raise ImportError(
            "google-analytics-data is not installed.\n"
            "Run: pip install google-analytics-data"
        )

    client = _get_client()
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    date_range = DateRange(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # ── Overview metrics ──────────────────────────────────────────────────────
    overview_resp = client.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[date_range],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="conversions"),
            Metric(name="bounceRate"),
        ],
    ))

    row = overview_resp.rows[0].metric_values if overview_resp.rows else [None] * 5

    def _val(idx: int, cast=float) -> float:
        v = row[idx].value if row[idx] else "0"
        return cast(v)

    overview = {
        "sessions":    int(_val(0)),
        "users":       int(_val(1)),
        "new_users":   int(_val(2)),
        "conversions": int(_val(3)),
        "bounce_rate": round(_val(4) * 100, 2),
    }

    # ── Top pages ─────────────────────────────────────────────────────────────
    pages_resp = client.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[date_range],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=10,
    ))
    top_pages = [
        {
            "page":     r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
        }
        for r in pages_resp.rows
    ]

    # ── Traffic sources ───────────────────────────────────────────────────────
    sources_resp = client.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[date_range],
        dimensions=[
            Dimension(name="sessionSource"),
            Dimension(name="sessionMedium"),
        ],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=10,
    ))
    traffic_sources = [
        {
            "source":   r.dimension_values[0].value,
            "medium":   r.dimension_values[1].value,
            "sessions": int(r.metric_values[0].value),
        }
        for r in sources_resp.rows
    ]

    return {
        "period":          {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "overview":        overview,
        "top_pages":       top_pages,
        "traffic_sources": traffic_sources,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GA4 weekly summary")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--property-id", type=str, default=None, help="GA4 property ID (overrides env var)")
    args = parser.parse_args()

    result = fetch_weekly_summary(property_id=args.property_id, days=args.days)
    print(json.dumps(result, indent=2))
