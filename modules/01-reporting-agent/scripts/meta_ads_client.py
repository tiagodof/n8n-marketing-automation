"""
Meta Ads Client — Module 01: AI Marketing Reporting Agent
Fetches campaign performance data from the Meta Marketing API.

Usage:
    python3 meta_ads_client.py
    python3 meta_ads_client.py --days 14

Required environment variables:
    META_ACCESS_TOKEN    — long-lived user or system access token
    META_AD_ACCOUNT_ID   — ad account ID in the format act_XXXXXXXXXX
"""

import os
import json
import argparse
from datetime import date, timedelta
from typing import Optional

import requests


META_API_BASE = "https://graph.facebook.com/v19.0"


def _get_credentials() -> tuple[str, str]:
    token = os.environ.get("META_ACCESS_TOKEN")
    account_id = os.environ.get("META_AD_ACCOUNT_ID")
    if not token:
        raise EnvironmentError(
            "META_ACCESS_TOKEN is not set. "
            "See .env.example for setup instructions."
        )
    if not account_id:
        raise EnvironmentError(
            "META_AD_ACCOUNT_ID is not set. "
            "See .env.example for setup instructions."
        )
    return token, account_id


def fetch_weekly_summary(
    account_id: Optional[str] = None,
    days: int = 7,
) -> dict:
    """
    Fetch a performance summary from Meta Ads for the last N days.

    Returns:
        {
            "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
            "totals": {
                "spend": float,
                "impressions": int,
                "clicks": int,
                "ctr": float       # percentage, e.g. 1.24
            },
            "campaigns": [
                {
                    "name": str,
                    "spend": float,
                    "impressions": int,
                    "clicks": int,
                    "ctr": float,
                    "roas": float   # 0.0 if no purchase events configured
                },
                ...
            ]
        }
    """
    token, default_account = _get_credentials()
    act = account_id or default_account

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    params = {
        "access_token": token,
        "time_range": json.dumps({"since": str(start_date), "until": str(end_date)}),
        "fields": "campaign_name,spend,impressions,clicks,ctr,purchase_roas",
        "level": "campaign",
        "limit": 50,
    }

    resp = requests.get(f"{META_API_BASE}/{act}/insights", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    campaigns = []
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0

    for row in data:
        spend       = float(row.get("spend", 0))
        impressions = int(row.get("impressions", 0))
        clicks      = int(row.get("clicks", 0))
        ctr         = float(row.get("ctr", 0))
        roas_list   = row.get("purchase_roas", [])
        roas        = float(roas_list[0]["value"]) if roas_list else 0.0

        total_spend       += spend
        total_impressions += impressions
        total_clicks      += clicks

        campaigns.append({
            "name":        row.get("campaign_name", "Unknown"),
            "spend":       round(spend, 2),
            "impressions": impressions,
            "clicks":      clicks,
            "ctr":         round(ctr, 4),
            "roas":        round(roas, 2),
        })

    overall_ctr = round(total_clicks / total_impressions * 100, 4) if total_impressions else 0.0

    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "totals": {
            "spend":       round(total_spend, 2),
            "impressions": total_impressions,
            "clicks":      total_clicks,
            "ctr":         overall_ctr,
        },
        "campaigns": sorted(campaigns, key=lambda c: c["spend"], reverse=True),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Meta Ads weekly summary")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--account-id", type=str, default=None, help="Ad account ID (overrides env var)")
    args = parser.parse_args()

    result = fetch_weekly_summary(account_id=args.account_id, days=args.days)
    print(json.dumps(result, indent=2))
