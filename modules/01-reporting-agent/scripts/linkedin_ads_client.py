"""LinkedIn Ads Client - Module 01: AI Marketing Reporting Agent.

Fetches campaign-level performance from the LinkedIn Reporting API.

Usage:
    python3 linkedin_ads_client.py
    python3 linkedin_ads_client.py --days 14

Required environment variables:
    LINKEDIN_ACCESS_TOKEN   OAuth access token with r_ads_reporting permission.
    LINKEDIN_AD_ACCOUNT_ID  Numeric LinkedIn advertising account ID.

Optional environment variables:
    LINKEDIN_API_VERSION    Version header for the REST API. Defaults to 202608.
    LINKEDIN_CAMPAIGN_NAMES JSON object mapping campaign IDs to human-readable names.

Official API reference:
https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting
"""

import argparse
import json
import os
from datetime import date, timedelta
from typing import Any, Mapping, Optional

import requests


LINKEDIN_ANALYTICS_URL = "https://api.linkedin.com/rest/adAnalytics"
DEFAULT_API_VERSION = "202608"


def _get_credentials() -> tuple[str, str]:
    """Return the OAuth token and ad account ID or raise a clear setup error."""
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    account_id = os.environ.get("LINKEDIN_AD_ACCOUNT_ID")

    if not access_token:
        raise EnvironmentError(
            "LINKEDIN_ACCESS_TOKEN is not set. "
            "Use an OAuth token with the r_ads_reporting permission."
        )
    if not account_id:
        raise EnvironmentError(
            "LINKEDIN_AD_ACCOUNT_ID is not set. "
            "See .env.example for setup instructions."
        )

    return access_token, account_id


def _load_campaign_names() -> dict[str, str]:
    """Load an optional campaign-ID-to-name mapping from the environment."""
    raw_mapping = os.environ.get("LINKEDIN_CAMPAIGN_NAMES", "{}")
    try:
        mapping = json.loads(raw_mapping)
    except json.JSONDecodeError as error:
        raise EnvironmentError(
            "LINKEDIN_CAMPAIGN_NAMES must be valid JSON, for example: "
            '{"123": "Lead Generation - Q3"}.'
        ) from error

    if not isinstance(mapping, dict):
        raise EnvironmentError("LINKEDIN_CAMPAIGN_NAMES must be a JSON object.")

    return {str(key): str(value) for key, value in mapping.items()}


def _date_range_value(start_date: date, end_date: date) -> str:
    """Build the LinkedIn REST dateRange query value."""
    return (
        "(start:(day:{start_day},month:{start_month},year:{start_year}),"
        "end:(day:{end_day},month:{end_month},year:{end_year}))"
    ).format(
        start_day=start_date.day,
        start_month=start_date.month,
        start_year=start_date.year,
        end_day=end_date.day,
        end_month=end_date.month,
        end_year=end_date.year,
    )


def _campaign_id(value: str) -> str:
    """Extract the numeric campaign ID from a sponsored campaign URN."""
    return str(value).rsplit(":", maxsplit=1)[-1]


def _campaign_urn(element: Mapping[str, Any]) -> str:
    """Read the campaign URN from the versioned API response.

    The current REST response returns pivotValues as a list. The single-value
    fallback preserves compatibility with older fixtures and stored responses.
    """
    pivot_values = element.get("pivotValues", [])
    if isinstance(pivot_values, list) and pivot_values:
        return str(pivot_values[0])
    return str(element.get("pivotValue", ""))


def _as_float(value: Any) -> float:
    """Safely convert API values that may be absent, numeric, or numeric strings."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    """Safely convert API values that may be absent, numeric, or numeric strings."""
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _headers(access_token: str) -> dict[str, str]:
    """Return headers required by the LinkedIn REST API."""
    return {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": os.environ.get("LINKEDIN_API_VERSION", DEFAULT_API_VERSION),
        "X-Restli-Protocol-Version": "2.0.0",
    }


def fetch_weekly_summary(
    account_id: Optional[str] = None,
    days: int = 7,
) -> dict[str, Any]:
    """Fetch campaign-level LinkedIn Ads performance for the last N complete days.

    The LinkedIn Ad Analytics endpoint returns impressions and clicks by default.
    This client explicitly requests spend, landing-page clicks, and conversion data.

    Returns a JSON-serialisable dictionary with period, totals, and campaign metrics.
    """
    if days < 1:
        raise ValueError("days must be at least 1.")

    access_token, default_account_id = _get_credentials()
    selected_account_id = account_id or default_account_id
    campaign_names = _load_campaign_names()

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    account_urn = f"urn:li:sponsoredAccount:{selected_account_id}"

    params = {
        "q": "analytics",
        "pivot": "CAMPAIGN",
        "timeGranularity": "ALL",
        "accounts": f"List({account_urn})",
        "dateRange": _date_range_value(start_date, end_date),
        "fields": (
            "impressions,clicks,costInLocalCurrency,landingPageClicks,"
            "externalWebsiteConversions"
        ),
    }

    response = requests.get(
        LINKEDIN_ANALYTICS_URL,
        headers=_headers(access_token),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    elements = response.json().get("elements", [])

    campaigns = []
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_landing_page_clicks = 0
    total_conversions = 0.0

    for element in elements:
        campaign_urn = _campaign_urn(element)
        campaign_id = _campaign_id(campaign_urn)
        impressions = _as_int(element.get("impressions"))
        clicks = _as_int(element.get("clicks"))
        spend = _as_float(element.get("costInLocalCurrency"))
        landing_page_clicks = _as_int(element.get("landingPageClicks"))
        conversions = _as_float(element.get("externalWebsiteConversions"))
        ctr = round((clicks / impressions) * 100, 4) if impressions else 0.0

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_landing_page_clicks += landing_page_clicks
        total_conversions += conversions

        campaigns.append(
            {
                "id": campaign_id,
                "name": campaign_names.get(campaign_id, campaign_urn or "Unknown campaign"),
                "spend": round(spend, 2),
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr,
                "landing_page_clicks": landing_page_clicks,
                "conversions": round(conversions, 2),
            }
        )

    overall_ctr = round((total_clicks / total_impressions) * 100, 4) if total_impressions else 0.0

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "totals": {
            "spend": round(total_spend, 2),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": overall_ctr,
            "landing_page_clicks": total_landing_page_clicks,
            "conversions": round(total_conversions, 2),
        },
        "campaigns": sorted(campaigns, key=lambda campaign: campaign["spend"], reverse=True),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch a LinkedIn Ads reporting summary.")
    parser.add_argument("--days", type=int, default=7, help="Number of completed days to include.")
    parser.add_argument("--account-id", help="Ad account ID that overrides LINKEDIN_AD_ACCOUNT_ID.")
    args = parser.parse_args()

    summary = fetch_weekly_summary(account_id=args.account_id, days=args.days)
    print(json.dumps(summary, indent=2))
