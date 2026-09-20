#!/usr/bin/env python3
"""Resolve the lead-image filenames referenced in raw/ wikitext to real URLs.

Standard library only. Companion to fetch_wiki.py: that script caches page
text, this one caches image *metadata* (a direct CDN URL + the credited
artist) via the MediaWiki imageinfo API - it never downloads image bytes.

Why metadata-only: most of these are individual fan art (Reddit/Instagram
handles, small studios), not Fandom's own work, and NOTICE.md already treats
the wiki's prose as something to keep off the open web for copyright reasons.
Hotlinking the same CDN URL the wiki itself serves, with credit shown and a
link back to the source page, keeps this app's exposure the same as browsing
the wiki - copying the pixels into this repo would be a step further than
that.

Usage:
    python3 tools/fetch_images.py            # resolve anything not yet cached
    python3 tools/fetch_images.py --refresh  # re-resolve everything
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_wiki import RAW_DIR, api_get  # noqa: E402

import build_dataset as bd  # noqa: E402

CACHE_PATH = RAW_DIR / "image_urls.json"


def referenced_filenames() -> list[str]:
    names: set[str] = set()
    for kind in ("achievements", "monsters"):
        for path in sorted((RAW_DIR / kind).glob("*.wikitext")):
            image = bd.extract_primary_image(path.read_text(encoding="utf-8"))
            if image:
                names.add(image["file"])
    return sorted(names)


def resolve_urls(filenames: list[str]) -> dict[str, str]:
    """Direct CDN URL for up to 50 File: titles per request."""
    out: dict[str, str] = {}
    titles = [f"File:{name}" for name in filenames]
    for i in range(0, len(titles), 50):
        batch = titles[i : i + 50]
        payload = api_get(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "imageinfo",
                "iiprop": "url",
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            # "missing" is set when the File: description page itself was
            # never created on this wiki, which happens even for images that
            # resolve fine on the shared media repository - imageinfo is the
            # real signal of whether the file exists, not "missing".
            info = page.get("imageinfo") or []
            if not info:
                continue
            title = page["title"]
            name = title.split(":", 1)[1] if ":" in title else title
            out[name] = info[0]["url"]
        print(f"  {min(i + 50, len(titles))}/{len(titles)}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-resolve everything")
    args = parser.parse_args()

    cached: dict[str, str] = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    wanted = referenced_filenames()
    print(f"{len(wanted)} distinct filenames referenced")

    todo = wanted if args.refresh else [f for f in wanted if f not in cached]
    print(f"{len(todo)} not yet cached")

    if todo:
        cached.update(resolve_urls(todo))
        CACHE_PATH.write_text(json.dumps(cached, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    missing = [f for f in wanted if f not in cached]
    if missing:
        print(f"{len(missing)} filenames never resolved (deleted/renamed on the wiki?):")
        for f in missing[:10]:
            print(f"  - {f}")

    print(f"cached -> {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
