"""Collect and normalise public competitor intelligence feeds.

This first Module 02 component reads a JSON configuration, collects RSS or Atom
feeds, and returns a stable item contract for the later AI curation and Slack
delivery steps. It intentionally uses public feed URLs only and never stores
credentials in the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_ITEM_LIMIT = 20
USER_AGENT = "n8n-marketing-automation/1.0 (+https://github.com/tiagodof/n8n-marketing-automation)"


def build_google_news_rss_url(
    query: str,
    language: str = "en-US",
    country: str = "US",
) -> str:
    """Build a public Google News RSS search URL for a competitor query."""
    if not query or not query.strip():
        raise ValueError("Google News queries must not be empty.")

    locale_language = language.strip()
    locale_country = country.strip().upper()
    params = urlencode(
        {
            "q": query.strip(),
            "hl": locale_language,
            "gl": locale_country,
            "ceid": f"{locale_country}:{locale_language.split('-')[0]}",
        }
    )
    return f"https://news.google.com/rss/search?{params}"


def build_reddit_rss_url(subreddit: str, sort: str = "new") -> str:
    """Build a public subreddit RSS URL without accepting unsafe path input."""
    cleaned_subreddit = subreddit.strip().removeprefix("r/")
    if not re.fullmatch(r"[A-Za-z0-9_]{2,21}", cleaned_subreddit):
        raise ValueError("Subreddit names must contain 2 to 21 letters, numbers, or underscores.")
    if sort not in {"new", "hot", "top", "rising"}:
        raise ValueError("Reddit sort must be one of: new, hot, top, rising.")
    return f"https://www.reddit.com/r/{cleaned_subreddit}/{sort}.rss"


def canonicalise_url(url: str) -> str:
    """Remove tracking parameters so the same item is not repeated in a digest."""
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()

    blocked_prefixes = ("utm_", "fbclid", "gclid")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(blocked_prefixes)
    ]
    return urlunparse(parsed._replace(query=urlencode(query), fragment=""))


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _clean_text(value: str) -> str:
    """Convert common feed markup into digest-ready plain text."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _child(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            return child
    return None


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if child.tag.rsplit("}", 1)[-1] == name]


def parse_feed(xml_content: bytes | str) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom content into source-neutral raw entries."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise ValueError(f"Feed is not valid XML: {exc}") from exc

    root_name = root.tag.rsplit("}", 1)[-1].lower()
    entries: list[dict[str, str]] = []

    if root_name == "rss":
        channel = _child(root, "channel")
        if channel is None:
            return entries
        for item in _children(channel, "item"):
            link = _text(_child(item, "link"))
            entries.append(
                {
                    "title": _text(_child(item, "title")),
                    "url": link,
                    "summary": _text(_child(item, "description")),
                    "published_at": _text(_child(item, "pubDate")),
                    "author": _text(_child(item, "author")) or _text(_child(item, "creator")),
                }
            )
        return entries

    if root_name == "feed":
        for entry in _children(root, "entry"):
            links = _children(entry, "link")
            author_element = _child(entry, "author")
            author = _text(_child(author_element, "name")) if author_element is not None else ""
            alternate_link = next(
                (
                    link.attrib.get("href", "")
                    for link in links
                    if link.attrib.get("rel", "alternate") == "alternate"
                ),
                "",
            )
            entries.append(
                {
                    "title": _text(_child(entry, "title")),
                    "url": alternate_link,
                    "summary": _text(_child(entry, "summary")) or _text(_child(entry, "content")),
                    "published_at": _text(_child(entry, "published")) or _text(_child(entry, "updated")),
                    "author": author,
                }
            )
        return entries

    raise ValueError("Only RSS and Atom feeds are supported.")


def _build_source_specs(config: dict[str, Any]) -> list[dict[str, str]]:
    """Expand configured source shortcuts into concrete public feed URLs."""
    sources: list[dict[str, str]] = []

    for index, source in enumerate(config.get("rss_feeds", []), start=1):
        url = str(source.get("url", "")).strip()
        if url:
            sources.append(
                {
                    "name": str(source.get("name") or f"RSS feed {index}"),
                    "type": "rss",
                    "url": url,
                }
            )

    google_news = config.get("google_news", {})
    if google_news.get("enabled"):
        for competitor in config.get("competitors", []):
            competitor_name = str(competitor.get("name") or "").strip()
            custom_query = str(competitor.get("google_news_query") or "").strip()
            query = custom_query or f'"{competitor_name}"'
            if not query:
                continue
            sources.append(
                {
                    "name": f"Google News: {competitor_name or query}",
                    "type": "google_news",
                    "url": build_google_news_rss_url(
                        query=query,
                        language=str(google_news.get("language", "en-US")),
                        country=str(google_news.get("country", "US")),
                    ),
                }
            )

    reddit = config.get("reddit", {})
    if reddit.get("enabled"):
        sort = str(reddit.get("sort", "new"))
        for subreddit in reddit.get("subreddits", []):
            cleaned_subreddit = str(subreddit).strip().removeprefix("r/")
            sources.append(
                {
                    "name": f"Reddit: r/{cleaned_subreddit}",
                    "type": "reddit",
                    "url": build_reddit_rss_url(cleaned_subreddit, sort=sort),
                }
            )

    return sources


def _matching_competitors(item_text: str, competitors: list[dict[str, Any]]) -> list[str]:
    lowered_text = item_text.casefold()
    matches: list[str] = []
    for competitor in competitors:
        name = str(competitor.get("name", "")).strip()
        terms = [name, *competitor.get("keywords", [])]
        if name and any(str(term).strip().casefold() in lowered_text for term in terms if str(term).strip()):
            matches.append(name)
    return matches


def _normalise_entry(
    raw_entry: dict[str, str],
    source: dict[str, str],
    competitors: list[dict[str, Any]],
    collected_at: str,
) -> dict[str, Any] | None:
    title = _clean_text(raw_entry.get("title", ""))
    url = canonicalise_url(raw_entry.get("url", ""))
    if not title or not url:
        return None

    summary = _clean_text(raw_entry.get("summary", ""))
    matches = _matching_competitors(f"{title} {summary}", competitors)
    item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return {
        "id": item_id,
        "title": title,
        "url": url,
        "summary": summary,
        "published_at": raw_entry.get("published_at", "").strip() or None,
        "author": raw_entry.get("author", "").strip() or None,
        "source": source["name"],
        "source_type": source["type"],
        "matched_competitors": matches,
        "collected_at": collected_at,
    }


def validate_config(config: dict[str, Any]) -> None:
    """Validate the small configuration contract before making network requests."""
    competitors = config.get("competitors")
    if not isinstance(competitors, list) or not competitors:
        raise ValueError("Configuration must include at least one competitor.")

    for competitor in competitors:
        if not isinstance(competitor, dict) or not str(competitor.get("name", "")).strip():
            raise ValueError("Each competitor must include a non-empty name.")
        keywords = competitor.get("keywords", [])
        if not isinstance(keywords, list):
            raise ValueError("Competitor keywords must be a list.")

    has_source = bool(config.get("rss_feeds"))
    has_source = has_source or bool(config.get("google_news", {}).get("enabled"))
    has_source = has_source or bool(config.get("reddit", {}).get("enabled"))
    if not has_source:
        raise ValueError("Enable Google News, Reddit, or at least one RSS feed.")


def collect_from_config(
    config: dict[str, Any],
    http_get: Callable[..., Any] = requests.get,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Collect public feeds and return a deduplicated, normalised item payload."""
    validate_config(config)
    collected_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    sources = _build_source_specs(config)
    item_limit = int(config.get("item_limit", DEFAULT_ITEM_LIMIT))
    if item_limit < 1:
        raise ValueError("item_limit must be at least 1.")

    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    competitors = config["competitors"]

    for source in sources:
        try:
            response = http_get(
                source["url"],
                headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml"},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            payload = getattr(response, "content", None) or getattr(response, "text", "")
            for raw_entry in parse_feed(payload)[:item_limit]:
                item = _normalise_entry(raw_entry, source, competitors, collected_at)
                if item:
                    items.append(item)
        except (requests.RequestException, ValueError) as exc:
            errors.append({"source": source["name"], "message": str(exc)})

    deduplicated: dict[str, dict[str, Any]] = {}
    for item in items:
        deduplicated.setdefault(item["url"], item)

    return {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "configured_competitors": [competitor["name"] for competitor in competitors],
        "sources_checked": len(sources),
        "items": list(deduplicated.values()),
        "errors": errors,
    }


def load_config(path: Path) -> dict[str, Any]:
    """Load a JSON configuration file with a concise error message."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Configuration file is not valid JSON: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public competitor intelligence feeds")
    parser.add_argument("--config", required=True, help="Path to the competitor configuration JSON file")
    parser.add_argument("--output", required=True, help="Path for the normalised intelligence JSON payload")
    args = parser.parse_args()

    try:
        result = collect_from_config(load_config(Path(args.config)))
    except (OSError, ValueError) as exc:
        print(f"Collection failed: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(result["items"]), "errors": len(result["errors"]), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
