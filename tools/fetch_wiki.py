#!/usr/bin/env python3
"""Fetch raw wikitext from the Dungeon Crawler Carl Fandom wiki.

Standard library only - no pip install needed.

This script ONLY downloads and caches. It does no parsing, so you can re-run
the parser (build_dataset.py) as many times as you like without hitting the
wiki again. Be polite: the cache is the point.

Usage:
    python3 tools/fetch_wiki.py                 # fetch everything into raw/
    python3 tools/fetch_wiki.py --only achievements
    python3 tools/fetch_wiki.py --refresh       # ignore cache, re-download
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://dungeon-crawler-carl.fandom.com/api.php"

# Identify ourselves. Fandom asks for a real UA; anonymous scrapers get blocked.
USER_AGENT = (
    "dcc-daily/0.1 (personal, non-commercial fan app; "
    "https://github.com/bar371/dcc-daily)"
)

# Seconds between requests. Do not lower this.
THROTTLE = 1.0

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"

# Which wiki categories feed which entry kind.
SOURCES = {
    "achievements": ["Category:Achievements"],
    "monsters": [
        "Category:Mob Types",
        "Category:Bosses",
    ],
}


def api_get(params: dict) -> dict:
    """One GET against the MediaWiki API, with retries and throttling."""
    params = dict(params, format="json", formatversion="2")
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            time.sleep(THROTTLE)
            if "error" in payload:
                raise RuntimeError(f"API error: {payload['error']}")
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            backoff = 2 ** attempt
            print(f"  retry in {backoff}s ({exc})", file=sys.stderr)
            time.sleep(backoff)

    raise RuntimeError(f"gave up on {url}") from last_error


def category_members(category: str) -> list[str]:
    """Every page title in a category, following continuation."""
    titles: list[str] = []
    cont: dict = {}
    while True:
        payload = api_get(
            {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": "500",
                "cmtype": "page",
                **cont,
            }
        )
        for member in payload.get("query", {}).get("categorymembers", []):
            titles.append(member["title"])
        if "continue" not in payload:
            return titles
        cont = payload["continue"]


def fetch_wikitext(titles: list[str]) -> dict[str, str]:
    """Raw wikitext for up to 50 titles per request."""
    out: dict[str, str] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i : i + 50]
        payload = api_get(
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": "|".join(batch),
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            if page.get("missing"):
                continue
            revisions = page.get("revisions") or []
            if not revisions:
                continue
            content = revisions[0].get("slots", {}).get("main", {}).get("content")
            if content:
                out[page["title"]] = content
        print(f"  {min(i + 50, len(titles))}/{len(titles)}")
    return out


def slug(title: str) -> str:
    """Filesystem-safe cache name.

    The readable part maps all punctuation to '_', so "A Trap?" and "A Trap!"
    would land on the same file. No collisions exist across the current 150
    achievement titles, but one new page could silently overwrite another's
    cache, so a short digest of the exact title is appended.
    """
    readable = "".join(c if c.isalnum() else "_" for c in title).strip("_")[:100]
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def harvest(kind: str, categories: list[str], refresh: bool) -> None:
    out_dir = RAW_DIR / kind
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n== {kind} ==")
    titles: list[str] = []
    for category in categories:
        print(f"listing {category}")
        found = category_members(category)
        print(f"  {len(found)} pages")
        titles.extend(found)

    titles = sorted(set(titles))

    if not refresh:
        titles = [t for t in titles if not (out_dir / f"{slug(t)}.wikitext").exists()]
        print(f"{len(titles)} not yet cached")

    if not titles:
        print("nothing to do")
        return

    print("fetching wikitext")
    for title, text in fetch_wikitext(titles).items():
        (out_dir / f"{slug(title)}.wikitext").write_text(text, encoding="utf-8")

    manifest = out_dir / "_titles.json"
    known = json.loads(manifest.read_text()) if manifest.exists() else {}
    known.update({slug(t): t for t in titles})
    manifest.write_text(json.dumps(known, indent=2, sort_keys=True), encoding="utf-8")
    print(f"cached -> {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(SOURCES), help="just one kind")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache")
    args = parser.parse_args()

    kinds = [args.only] if args.only else list(SOURCES)
    for kind in kinds:
        harvest(kind, SOURCES[kind], args.refresh)

    print("\nDone. Next: python3 tools/build_dataset.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
