"""Unit tests for Module 02 public feed collection."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import feed_collector


RSS_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss version='2.0'>
  <channel>
    <title>Example feed</title>
    <item>
      <title>Acme launches new analytics feature</title>
      <link>https://news.example.com/acme-feature?utm_source=rss</link>
      <description>Acme has released a competitor analytics feature.</description>
      <pubDate>Wed, 24 Sep 2026 10:00:00 GMT</pubDate>
      <author>Newsroom</author>
    </item>
  </channel>
</rss>"""

ATOM_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <title>Atom example</title>
  <entry>
    <title>Acme enters a new market</title>
    <link rel='alternate' href='https://blog.example.com/acme-market'/>
    <summary>New update from Acme.</summary>
    <published>2026-09-24T11:30:00Z</published>
    <author><name>Example team</name></author>
  </entry>
</feed>"""


class FakeResponse:
    def __init__(self, content, status_error=None):
        self.content = content
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error


class TestFeedUrlBuilders(unittest.TestCase):
    def test_google_news_url_uses_query_and_locale(self):
        url = feed_collector.build_google_news_rss_url("Acme launch", "pt-BR", "br")
        self.assertIn("news.google.com/rss/search", url)
        self.assertIn("q=Acme+launch", url)
        self.assertIn("hl=pt-BR", url)
        self.assertIn("gl=BR", url)
        self.assertIn("ceid=BR%3Apt", url)

    def test_google_news_requires_query(self):
        with self.assertRaises(ValueError):
            feed_collector.build_google_news_rss_url(" ")

    def test_reddit_url_normalises_prefix(self):
        self.assertEqual(
            feed_collector.build_reddit_rss_url("r/marketing", "new"),
            "https://www.reddit.com/r/marketing/new.rss",
        )

    def test_reddit_url_rejects_unsafe_name(self):
        with self.assertRaises(ValueError):
            feed_collector.build_reddit_rss_url("marketing/news")

    def test_default_google_news_query_uses_exact_competitor_name(self):
        sources = feed_collector._build_source_specs(
            {
                "competitors": [{"name": "Acme Analytics", "keywords": []}],
                "google_news": {"enabled": True, "language": "en-US", "country": "US"},
            }
        )
        self.assertIn("q=%22Acme+Analytics%22", sources[0]["url"])


class TestFeedParsing(unittest.TestCase):
    def test_parses_rss_entry(self):
        entries = feed_collector.parse_feed(RSS_XML)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Acme launches new analytics feature")
        self.assertEqual(entries[0]["author"], "Newsroom")

    def test_parses_atom_entry(self):
        entries = feed_collector.parse_feed(ATOM_XML)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["url"], "https://blog.example.com/acme-market")
        self.assertEqual(entries[0]["author"], "Example team")

    def test_normalisation_removes_feed_markup(self):
        entry = feed_collector.parse_feed(
            b"<rss><channel><item><title>Acme update</title><link>https://example.com</link><description><b>Acme</b> &amp;amp; news</description></item></channel></rss>"
        )[0]
        item = feed_collector._normalise_entry(
            entry,
            {"name": "Example", "type": "rss", "url": "https://example.com/feed"},
            [{"name": "Acme", "keywords": []}],
            "2026-09-24T00:00:00Z",
        )
        self.assertEqual(item["summary"], "Acme & news")

    def test_invalid_xml_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "not valid XML"):
            feed_collector.parse_feed(b"not xml")

    def test_canonicalise_url_removes_tracking_values(self):
        url = "https://news.example.com/story?utm_source=rss&ref=home&fbclid=abc#fragment"
        self.assertEqual(
            feed_collector.canonicalise_url(url),
            "https://news.example.com/story?ref=home",
        )


class TestCollection(unittest.TestCase):
    CONFIG = {
        "item_limit": 5,
        "competitors": [{"name": "Acme", "keywords": ["Acme Analytics"]}],
        "google_news": {"enabled": False},
        "reddit": {"enabled": False},
        "rss_feeds": [
            {"name": "News A", "url": "https://feeds.example.com/a.xml"},
            {"name": "News B", "url": "https://feeds.example.com/b.xml"},
        ],
    }

    def test_normalises_matches_and_deduplicates_items(self):
        def fake_get(url, **_kwargs):
            return FakeResponse(RSS_XML)

        result = feed_collector.collect_from_config(self.CONFIG, http_get=fake_get)

        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["sources_checked"], 2)
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["url"], "https://news.example.com/acme-feature")
        self.assertEqual(item["matched_competitors"], ["Acme"])
        self.assertEqual(item["source_type"], "rss")
        self.assertTrue(item["id"])

    def test_keeps_source_failure_as_error_without_stopping_collection(self):
        def fake_get(url, **_kwargs):
            if url.endswith("a.xml"):
                return FakeResponse(RSS_XML)
            raise feed_collector.requests.RequestException("temporary failure")

        result = feed_collector.collect_from_config(self.CONFIG, http_get=fake_get)

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["source"], "News B")

    def test_config_requires_competitor(self):
        with self.assertRaisesRegex(ValueError, "at least one competitor"):
            feed_collector.collect_from_config(
                {"competitors": [], "rss_feeds": [{"name": "Feed", "url": "https://example.com/feed"}]}
            )

    def test_config_requires_source(self):
        with self.assertRaisesRegex(ValueError, "Enable Google News"):
            feed_collector.collect_from_config({"competitors": [{"name": "Acme", "keywords": []}]})


if __name__ == "__main__":
    unittest.main()
