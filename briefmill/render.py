"""Render issues into a single static site."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from briefmill.issues import Issue, load_issues, validate


def load_config(root: Path) -> dict:
    path = root / "config.json"
    config = {
        "product_name": "本周可做",
        "tagline": "",
        "price_label": "",
        "payment_url": "",
        "payment_label": "订阅",
    }
    if path.exists():
        config.update(json.loads(path.read_text(encoding="utf-8")))
    return config


def render_site(root: Path) -> Path:
    issues = load_issues(root)
    if not issues:
        raise ValueError("no issues to render")
    for issue in issues:
        validate(issue)
    config = load_config(root)
    fetched_at = _fetched_at(root)
    site = root / "site"
    issue_dir = site / "issues"
    issue_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for issue in issues:
        filename = f"{issue.date}.html"
        page = _page(
            config,
            issue.title,
            _article(issue),
            _archive(issues, issue.date, nested=True),
            fetched_at,
            filename,
        )
        (issue_dir / filename).write_text(page, encoding="utf-8")
        pages.append(filename)
    home = _page(
        config,
        issues[0].title,
        _article(issues[0]),
        _archive(issues, issues[0].date, nested=False),
        fetched_at,
        "index.html",
    )
    (site / "index.html").write_text(home, encoding="utf-8")
    return site / "index.html"


def render_markdown(text: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_items() -> None:
        if items:
            body = "".join(f"<li>{render_inline(item)}</li>" for item in items)
            blocks.append(f"<ul>{body}</ul>")
            items.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_items()
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            flush_items()
            blocks.append(f"<h3>{escape(stripped[3:].strip())}</h3>")
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            items.append(stripped[2:].strip())
            continue
        flush_items()
        paragraph.append(stripped)
    flush_paragraph()
    flush_items()
    return "\n".join(blocks)


def render_inline(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _article(issue: Issue) -> str:
    summary = f"<p class=\"summary\">{escape(issue.summary)}</p>" if issue.summary else ""
    product = f"<p class=\"product\">本周产品：{escape(issue.product)}</p>" if issue.product else ""
    return (
        f"<article>"
        f"<p class=\"date\">{escape(issue.date)}</p>"
        f"<h2>{escape(issue.title)}</h2>"
        f"{summary}{product}"
        f"{render_markdown(issue.body)}"
        f"</article>"
    )


def _archive(issues: list[Issue], current: str, *, nested: bool) -> str:
    if len(issues) < 2:
        return ""
    links = []
    for issue in issues:
        latest = issue.date == issues[0].date
        if latest:
            href = "../index.html" if nested else "index.html"
        else:
            href = f"{issue.date}.html" if nested else f"issues/{issue.date}.html"
        mark = " aria-current=\"page\"" if issue.date == current else ""
        links.append(
            f"<li><a href=\"{href}\"{mark}>{escape(issue.date)} {escape(issue.title)}</a></li>"
        )
    return "<nav><p class=\"kicker\">往期</p><ul>" + "".join(links) + "</ul></nav>"


def _page(config: dict, title: str, article: str, archive: str, fetched_at: str, filename: str) -> str:
    home = "../index.html" if filename != "index.html" else "index.html"
    payment = _payment(config)
    fetched = f"<p class=\"fine\">公开来源抓取于 {escape(fetched_at)}。分数和排名此后会变。</p>" if fetched_at else ""
    name = escape(str(config["product_name"]))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · {name}</title>
  <style>
    :root {{
      --paper: #f3efe4;
      --ink: #1e1a16;
      --rust: #8f3d1b;
      --quiet: #5e564c;
      --rule: #d8d0c2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Palatino Linotype", Palatino, "Songti SC", "Noto Serif SC", serif;
      line-height: 1.7;
    }}
    .wrap {{ max-width: 42rem; margin: 0 auto; padding: 3.2rem 1.3rem 4.5rem; }}
    a {{ color: var(--rust); }}
    .kicker {{
      margin: 0;
      color: var(--rust);
      font-family: "Segoe UI", sans-serif;
      font-size: 0.74rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0.35rem 0 0.4rem;
      font-size: 3rem;
      font-weight: 500;
      line-height: 1.05;
      letter-spacing: -0.03em;
    }}
    h1 a {{ color: inherit; text-decoration: none; }}
    .tagline {{ margin: 0; color: var(--quiet); font-size: 1.08rem; }}
    .bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.8rem 1rem;
      align-items: center;
      margin: 1.3rem 0 2rem;
      padding-bottom: 1.2rem;
      border-bottom: 1px solid var(--rule);
      font-family: "Segoe UI", sans-serif;
    }}
    .price {{ margin: 0; }}
    .pay, .closed {{
      display: inline-block;
      padding: 0.45rem 0.8rem;
      background: var(--ink);
      color: var(--paper);
      text-decoration: none;
    }}
    .closed {{ background: transparent; color: var(--quiet); border: 1px solid var(--rule); }}
    .date {{ margin: 0; color: var(--rust); font-family: "Segoe UI", sans-serif; font-size: 0.92rem; }}
    h2 {{ margin: 0.25rem 0 0.8rem; font-size: 1.85rem; font-weight: 500; line-height: 1.25; }}
    h3 {{ margin: 1.6rem 0 0.4rem; font-size: 1.15rem; font-weight: 650; }}
    .summary {{ font-size: 1.12rem; }}
    .product {{ color: var(--quiet); }}
    ul {{ padding-left: 1.15rem; }}
    li {{ margin: 0.35rem 0; }}
    nav {{ margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--rule); }}
    nav ul {{ list-style: none; padding: 0; }}
    .fine {{ margin-top: 2rem; color: var(--quiet); font-size: 0.92rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <p class="kicker">Weekly build</p>
      <h1><a href="{home}">{name}</a></h1>
      <p class="tagline">{escape(str(config.get("tagline", "")))}</p>
      <div class="bar">
        <p class="price">{escape(str(config.get("price_label", "")))}</p>
        {payment}
      </div>
    </header>
    {article}
    {archive}
    {fetched}
  </div>
</body>
</html>
"""


def _payment(config: dict) -> str:
    url = str(config.get("payment_url") or "").strip()
    label = escape(str(config.get("payment_label") or "订阅"))
    if url.startswith("https://"):
        return f'<a class="pay" href="{escape(url)}">{label}</a>'
    return '<span class="closed">订阅还未开放</span>'


def _fetched_at(root: Path) -> str:
    path = root / "data" / "sources.json"
    if not path.exists():
        return ""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("fetched_at") or "")
