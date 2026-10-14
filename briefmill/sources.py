"""Download public feeds into a small JSON snapshot the issue must cite."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

FEEDS = (
    ("hn", "Hacker News 首页", "https://hnrss.org/frontpage?count=15"),
    (
        "gh",
        "GitHub 今日趋势",
        "https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml",
    ),
)
USER_AGENT = "briefmill/1.0 (+local weekly brief)"
ITEM_LIMIT = 12
SNIPPET_LIMIT = 4000


def sources_path(root: Path) -> Path:
    return root / "data" / "sources.json"


def fetch(root: Path, timeout: float = 25) -> dict:
    previous = _read_json(sources_path(root))
    previous_feeds = {feed["id"]: feed for feed in previous.get("feeds", [])}
    feeds = []
    errors = []
    for feed_id, title, url in FEEDS:
        try:
            xml_bytes = _download(url, timeout)
            feeds.append(_parse_feed(feed_id, title, url, xml_bytes))
        except (URLError, TimeoutError, ElementTree.ParseError, OSError) as exc:
            errors.append({"id": feed_id, "error": str(exc)})
            if feed_id in previous_feeds:
                feeds.append(previous_feeds[feed_id])
    if not feeds:
        raise RuntimeError("all feeds failed: " + json.dumps(errors, ensure_ascii=False))
    payload = {
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "feeds": feeds,
        "errors": errors,
    }
    path = sources_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _download(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _parse_feed(feed_id: str, title: str, url: str, xml_bytes: bytes) -> dict:
    root = ElementTree.fromstring(xml_bytes)
    channel = root.find("channel")
    updated = ""
    if channel is not None:
        updated = (channel.findtext("lastBuildDate") or channel.findtext("pubDate") or "").strip()
    items = []
    for node in root.findall(".//item")[:ITEM_LIMIT]:
        description = node.findtext("description") or ""
        plain = _plain(description)
        points = _first_int(r"Points:\s*(\d+)", plain)
        comments = _first_int(r"# Comments:\s*(\d+)", plain)
        items.append(
            {
                "title": (node.findtext("title") or "").strip(),
                "link": (node.findtext("link") or "").strip(),
                "points": points,
                "comments": comments,
                "discussion": (node.findtext("comments") or "").strip(),
                "snippet": _snippet(plain),
            }
        )
    return {
        "id": feed_id,
        "title": title,
        "url": url,
        "updated": updated,
        "items": [item for item in items if item["title"] and item["link"]],
    }


def _plain(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _snippet(plain: str) -> str:
    text = re.sub(r"Article URL:\s*\S+", "", plain)
    text = re.sub(r"Comments URL:\s*\S+", "", text)
    text = re.sub(r"Points:\s*\d+", "", text)
    text = re.sub(r"# Comments:\s*\d+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:SNIPPET_LIMIT]


def _first_int(pattern: str, value: str) -> int | None:
    match = re.search(pattern, value)
    if match is None:
        return None
    return int(match.group(1))


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
