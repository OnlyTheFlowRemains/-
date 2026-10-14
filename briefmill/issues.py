"""Load and validate one weekly issue."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED_SECTIONS = (
    "信号",
    "本周产品",
    "谁付钱",
    "最小范围",
    "不做什么",
    "定价",
    "来源",
)


@dataclass(frozen=True)
class Issue:
    path: Path
    date: str
    title: str
    summary: str
    product: str
    body: str

    @property
    def sections(self) -> dict[str, str]:
        found: dict[str, list[str]] = {}
        current: str | None = None
        for line in self.body.splitlines():
            if line.startswith("## "):
                current = line[3:].strip()
                found[current] = []
                continue
            if current is not None:
                found[current].append(line)
        return {name: "\n".join(lines).strip() for name, lines in found.items()}


def issues_dir(root: Path) -> Path:
    return root / "issues"


def load_issues(root: Path) -> list[Issue]:
    directory = issues_dir(root)
    if not directory.exists():
        return []
    loaded = [load_issue(path) for path in sorted(directory.glob("*.md"))]
    return sorted(loaded, key=lambda issue: issue.date, reverse=True)


def load_issue(path: Path) -> Issue:
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(raw)
    date = meta.get("date", "").strip()
    title = meta.get("title", "").strip()
    if not date or not title:
        raise ValueError(f"{path.name} needs date and title")
    if path.stem != date:
        raise ValueError(f"{path.name} filename must match date {date}")
    return Issue(
        path=path,
        date=date,
        title=title,
        summary=meta.get("summary", "").strip(),
        product=meta.get("product", "").strip(),
        body=body.strip(),
    )


def validate(issue: Issue) -> None:
    missing = [name for name in REQUIRED_SECTIONS if not issue.sections.get(name)]
    if missing:
        raise ValueError(f"{issue.path.name} missing sections: {', '.join(missing)}")
    if not issue.product:
        raise ValueError(f"{issue.path.name} needs a product name")


def _split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", raw, re.S)
    if match is None:
        raise ValueError("issue must start with frontmatter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"bad frontmatter line: {line}")
        meta[key.strip()] = value.strip()
    return meta, match.group(2)
