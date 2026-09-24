# Module 02: Competitor Intelligence Monitor

## What this stage delivers

This module will turn public competitor signals into a focused daily Slack digest. **Step 7** establishes the collection foundation: configurable competitors, public RSS ingestion, Reddit feed ingestion, Google News search feeds, source-level error isolation, URL deduplication, and a normalised data contract.

No API credential is needed for this stage. The collector does not scrape restricted pages, access private Reddit feeds, or make decisions about an item. AI relevance scoring, Slack formatting, and the scheduled n8n workflow are the next increment.

## Architecture, current stage

```text
competitor configuration
          |
          v
RSS feeds, Reddit feeds, Google News search feeds
          |
          v
feed_collector.py
          |
          v
normalised intelligence JSON
          |
          v
AI curation, Slack digest, and n8n schedule (next step)
```

## Components

| Component | Responsibility |
|---|---|
| `examples/competitors.example.json` | Starting point for the competitor list and public source settings. |
| `scripts/feed_collector.py` | Builds public Google News and Reddit feed URLs, fetches feeds, normalises entries, detects configured competitor mentions, and isolates source errors. |
| `tests/test_feed_collector.py` | Tests URL builders, RSS and Atom parsing, tracking-parameter removal, item deduplication, matching, and failure handling. |

## Configuration

Copy the example outside version control and replace the placeholder competitor data:

```bash
cp modules/02-competitor-monitor/examples/competitors.example.json \
  /tmp/competitors.json
```

Each competitor needs a name and may include extra matching keywords. The collector supports three public source groups:

| Source group | Configuration | Use |
|---|---|---|
| RSS feeds | `rss_feeds` | Any public publisher, blog, or industry feed. |
| Google News | `google_news` and competitor names or `google_news_query` | Search feeds scoped by competitor and locale. |
| Reddit | `reddit.subreddits` | Public subreddit listing feeds, such as `r/marketing/new.rss`. |

A Google News search feed is generated for every configured competitor when `google_news.enabled` is true. The default query uses the competitor name as an exact phrase. It can be overridden per competitor with `google_news_query`, for example `"Example Competitor" OR examplecompetitor`.

## Run the collector

```bash
python3 modules/02-competitor-monitor/scripts/feed_collector.py \
  --config /tmp/competitors.json \
  --output /tmp/competitor-intelligence.json
```

The JSON output is designed as the handoff to the next stage. Each item includes a deterministic URL-based ID, title, canonical URL, plain-text summary, source, source type, publication information when available, matching competitor names, and UTC collection time. Duplicate URLs are removed after tracking parameters such as `utm_source` and `fbclid` are stripped.

A failed source is reported in the output `errors` list instead of cancelling the complete collection run. This makes the future daily workflow observable and resilient when a publisher feed is temporarily unavailable.

## Tests

Run the Module 02 tests with:

```bash
python3 -m unittest discover \
  -s modules/02-competitor-monitor/tests \
  -p 'test_*.py' \
  -v
```

## Next increment

The next stage will add AI relevance filtering, Slack Block Kit formatting, and an importable n8n workflow that creates the daily digest. The collector output remains deliberately source-neutral so that this layer can be tested without live feeds or Slack credentials.

## References

[1]: https://news.google.com/rss "Google News RSS"
[2]: https://www.reddit.com/r/raerth/comments/etibb/guide_reddit_rss/ "Guide: Reddit and RSS"
