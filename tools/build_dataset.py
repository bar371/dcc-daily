#!/usr/bin/env python3
"""Turn cached wikitext (raw/) into the app dataset (data/entries.json).

Standard library only.

The hard part is the spoiler tier. Three signals, in order of trust:

  1. CITATION  - the page cites a book by name, e.g. "Dinniman, Matt.
                 ''The Butcher's Masquerade'' (Chapter 8)". The lowest-numbered
                 book cited is where the entry first appears. Most reliable.
  2. FLOOR     - the page sits in a "Floor N Achievements" category. Floors map
                 to books via config/books.json.
  3. NONE      - fall back to config.unknownTierPolicy (default: hide).

Every entry records which signal was used, so you can audit before shipping:

    python3 tools/build_dataset.py --report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"
DATA_DIR = REPO_ROOT / "data"
CONFIG = REPO_ROOT / "config" / "books.json"

WIKI_BASE = "https://dungeon-crawler-carl.fandom.com/wiki/"

# ---------------------------------------------------------------- wikitext ---

RE_REF = re.compile(r"<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE)
RE_SELFCLOSING_REF = re.compile(r"<ref[^>]*/>", re.IGNORECASE)
RE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
RE_FILE = re.compile(r"\[\[(?:File|Image):[^\]]*\]\]", re.IGNORECASE)
RE_CATEGORY = re.compile(r"\[\[Category:([^\]|]+)(?:\|[^\]]*)?\]\]", re.IGNORECASE)
RE_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]")
RE_BOLD_ITALIC = re.compile(r"'{2,5}")
RE_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
RE_HEADING = re.compile(r"^\s*={2,}\s*(.+?)\s*={2,}\s*$", re.MULTILINE)
RE_FLOOR_CAT = re.compile(r"Floor\s+(\d+)\s+Achievements", re.IGNORECASE)
RE_REWARD = re.compile(r"^\s*'*Reward:'*\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_WS = re.compile(r"[ \t]+")
RE_BLANKS = re.compile(r"\n{3,}")


def strip_markup(text: str) -> str:
    """Wikitext -> readable plain text. Deliberately lossy."""
    text = RE_COMMENT.sub("", text)
    text = RE_REF.sub("", text)
    text = RE_SELFCLOSING_REF.sub("", text)
    text = RE_FILE.sub("", text)
    text = RE_CATEGORY.sub("", text)
    # Collapse nested templates from the inside out.
    for _ in range(6):
        new = RE_TEMPLATE.sub("", text)
        if new == text:
            break
        text = new
    text = RE_LINK.sub(r"\1", text)
    text = RE_BOLD_ITALIC.sub("", text)
    text = re.sub(r"^\s*[*#:;]+\s?", "", text, flags=re.MULTILINE)
    text = RE_WS.sub(" ", text)
    text = RE_BLANKS.sub("\n\n", text)
    return text.strip()


def extract_quote_block(wikitext: str) -> tuple[str, str]:
    """Pull the System AI text out. Returns (text, strategy_used)."""
    # 1. An explicit quote template - the wiki's usual way of framing System AI text.
    match = re.search(
        r"\{\{\s*(?:quote|Quote|blockquote|AI|System)\s*\|(.+?)\}\}",
        wikitext,
        re.DOTALL,
    )
    if match:
        body = match.group(1)
        # Drop named template params (|author=..., |source=...).
        body = re.split(r"\|\s*\w+\s*=", body)[0]
        cleaned = strip_markup(body)
        if len(cleaned) > 40:
            return cleaned, "template"

    # 2. A leading indented block (": " lines) before the first heading.
    head = RE_HEADING.split(wikitext)[0]
    indented = [ln[1:].strip() for ln in head.splitlines() if ln.startswith(":")]
    if indented:
        cleaned = strip_markup("\n".join(indented))
        if len(cleaned) > 40:
            return cleaned, "indent"

    # 3. Whatever prose sits before the first heading.
    cleaned = strip_markup(head)
    if len(cleaned) > 40:
        return cleaned, "lead"

    return "", "none"


# ------------------------------------------------------------ spoiler tier ---


def build_citation_index(books: list[dict]) -> list[tuple[re.Pattern, int]]:
    patterns: list[tuple[re.Pattern, int]] = []
    for book in books:
        for alias in book.get("citationAliases", []):
            if not alias.strip():
                continue
            patterns.append((re.compile(re.escape(alias), re.IGNORECASE), book["index"]))
    return patterns


def floor_to_book(books: list[dict]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for book in books:
        for floor in book.get("floors", []):
            mapping[floor] = book["index"]
    return mapping


def resolve_tier(
    wikitext: str,
    citation_patterns: list[tuple[re.Pattern, int]],
    floor_map: dict[int, int],
) -> tuple[int | None, str, int | None]:
    """Returns (tier, signal, floor)."""
    cited = {idx for pattern, idx in citation_patterns if pattern.search(wikitext)}

    floors = {int(m) for m in RE_FLOOR_CAT.findall(wikitext)}
    floor = min(floors) if floors else None

    if cited:
        return min(cited), "citation", floor
    if floor is not None and floor in floor_map:
        return floor_map[floor], "floor", floor
    return None, "none", floor


# ------------------------------------------------------------------ build ---


def clean_title(raw_title: str) -> str:
    return re.sub(r"\s+Achievement$", "", raw_title).strip()


def entry_id(kind: str, title: str) -> str:
    digest = hashlib.sha1(f"{kind}:{title}".encode()).hexdigest()[:10]
    return f"{kind[:3]}_{digest}"


def build_kind(kind: str, config: dict, verbose: bool) -> tuple[list[dict], dict]:
    src_dir = RAW_DIR / kind
    if not src_dir.exists():
        print(f"skip {kind}: no raw/{kind} (run tools/fetch_wiki.py first)")
        return [], {}

    titles_path = src_dir / "_titles.json"
    titles = json.loads(titles_path.read_text()) if titles_path.exists() else {}

    citation_patterns = build_citation_index(config["books"])
    floor_map = floor_to_book(config["books"])

    entries: list[dict] = []
    stats = {"citation": 0, "floor": 0, "none": 0, "no_body": 0, "total": 0}

    for path in sorted(src_dir.glob("*.wikitext")):
        wikitext = path.read_text(encoding="utf-8")
        raw_title = titles.get(path.stem, path.stem.replace("_", " "))

        # Index pages ("Floor 3 Achievements") are navigation, not entries.
        if RE_FLOOR_CAT.fullmatch(raw_title.strip()):
            continue

        body, strategy = extract_quote_block(wikitext)
        tier, signal, floor = resolve_tier(wikitext, citation_patterns, floor_map)

        # Look in the extracted body first: strip_markup() deletes templates
        # wholesale, so a Reward line inside {{Quote|...}} only survives here.
        reward_match = RE_REWARD.search(body) or RE_REWARD.search(strip_markup(wikitext))
        reward = reward_match.group(1).strip() if reward_match else None
        if reward:
            # Drop the whole "Reward: ..." line from the body so the app can
            # style it separately instead of printing it twice.
            body = RE_REWARD.sub("", body).strip()

        stats["total"] += 1
        stats[signal] += 1
        if not body:
            stats["no_body"] += 1

        entries.append(
            {
                "id": entry_id(kind, raw_title),
                "kind": kind,
                "title": clean_title(raw_title),
                "body": body,
                "reward": reward,
                "spoilerTier": tier,
                "tierSignal": signal,
                "floor": floor,
                "bodySource": strategy,
                "sourceUrl": WIKI_BASE + raw_title.replace(" ", "_"),
            }
        )

        if verbose and (signal == "none" or not body):
            print(f"  ? {raw_title}  signal={signal} body={strategy}")

    return entries, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="list problem pages")
    parser.add_argument(
        "--include-unknown",
        action="store_true",
        help="emit entries with no resolved tier (overrides unknownTierPolicy)",
    )
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text())
    policy = config.get("unknownTierPolicy", "hide")
    max_tier = max(b["index"] for b in config["books"])

    all_entries: list[dict] = []
    for kind in ("achievements", "monsters"):
        entries, stats = build_kind(kind, config, args.report)
        if stats:
            print(
                f"{kind}: {stats['total']} pages | "
                f"tier by citation {stats['citation']}, by floor {stats['floor']}, "
                f"unresolved {stats['none']} | missing body {stats['no_body']}"
            )
        all_entries.extend(entries)

    if not all_entries:
        print("\nNo entries. Run: python3 tools/fetch_wiki.py", file=sys.stderr)
        return 1

    kept: list[dict] = []
    for entry in all_entries:
        if not entry["body"]:
            continue
        if entry["spoilerTier"] is None:
            if args.include_unknown or policy == "show":
                entry["spoilerTier"] = 1 if policy == "show" else max_tier
            elif policy == "max":
                entry["spoilerTier"] = max_tier
            else:
                continue
        kept.append(entry)

    kept.sort(key=lambda e: (e["spoilerTier"], e["kind"], e["title"]))

    dataset = {
        "version": 1,
        "source": "Dungeon Crawler Carl Wiki (Fandom)",
        "license": "CC BY-SA 3.0 - see NOTICE.md",
        "books": [
            {"index": b["index"], "title": b["title"], "short": b["short"]}
            for b in config["books"]
        ],
        "entries": kept,
    }

    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / "entries.json"
    out.write_text(json.dumps(dataset, indent=1, ensure_ascii=False), encoding="utf-8")

    by_tier: dict[int, int] = {}
    for entry in kept:
        by_tier[entry["spoilerTier"]] = by_tier.get(entry["spoilerTier"], 0) + 1
    spread = ", ".join(f"B{t}:{n}" for t, n in sorted(by_tier.items()))

    print(f"\nwrote {out} - {len(kept)} entries ({spread})")
    if len(kept) < 60:
        print("WARNING: thin dataset. A daily app wants 150+ or it repeats fast.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
