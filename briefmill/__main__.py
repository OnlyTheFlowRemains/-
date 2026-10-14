"""CLI: python -m briefmill fetch|check|render|serve"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from briefmill.issues import load_issues, validate
from briefmill.render import render_site
from briefmill.sources import fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="briefmill")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    sub.add_parser("check")
    sub.add_parser("render")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.cmd == "fetch":
        payload = fetch(root)
        count = sum(len(feed["items"]) for feed in payload["feeds"])
        print(f"fetched {count} items, errors {len(payload['errors'])}")
        return 0
    if args.cmd == "check":
        issues = load_issues(root)
        if not issues:
            raise SystemExit("no issues")
        for issue in issues:
            validate(issue)
            print(f"ok {issue.date} {issue.product}")
        return 0
    if args.cmd == "render":
        print(render_site(root))
        return 0
    if args.cmd == "serve":
        site = root / "site"
        if not (site / "index.html").exists():
            render_site(root)
        handler = partial(SimpleHTTPRequestHandler, directory=str(site))
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
        print(f"http://127.0.0.1:{args.port}")
        server.serve_forever()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
