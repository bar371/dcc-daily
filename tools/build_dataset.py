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
RE_BOLD_ITALIC = re.compile(r"'{2,}")
RE_REDIRECT = re.compile(r"^\s*#REDIRECT\b", re.IGNORECASE)
RE_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
RE_HEADING = re.compile(r"^\s*={2,}\s*(.+?)\s*={2,}\s*$", re.MULTILINE)
# Title of a per-floor index/nav page ("Floor 3 Achievements"), not a real entry.
RE_FLOOR_INDEX_TITLE = re.compile(r"^Floor\s+\d+\s+Achievements$", re.IGNORECASE)
# The generic "what is an Achievement/Boss" mechanic-overview page for each
# category tags itself into its own category, so the crawl picks it up
# alongside real entries. It isn't one - drop it by exact title.
META_PAGE_TITLES = {
    "achievements": {"Achievement", "Achievements"},
    "monsters": {"Boss", "Bosses", "Mob Types", "Monster", "Monsters"},
}
# Real pages tag a plain [[Category:Floor N]] - never the "Floor N Achievements"
# form the fixtures originally guessed at. Keep this narrow (bracketed category
# syntax only) so prose like "he arrived on Floor 3" can't false-positive.
RE_FLOOR_CAT = re.compile(r"\[\[Category:Floor\s+(\d+)\]\]", re.IGNORECASE)
# The wiki cites source material as {{cite|BOOK|chapter}} (inline) or
# {{ref|BOOK|chapter}} (inside <ref> footnotes) - not spelled-out book titles.
# BOOK is already the book index from config/books.json.
RE_CITE_TEMPLATE = re.compile(r"\{\{\s*(?:cite|ref)\s*\|\s*(\d+)\s*\|", re.IGNORECASE)
# A whole {{cite|..}}/{{ref|..}} call (never nests further) - stripped before
# hunting for an OUTER {{quote|...}}, whose own naive non-greedy regex would
# otherwise stop at the citation's inner "}}" instead of its own.
RE_CITE_INLINE = re.compile(r"\{\{\s*(?:cite|ref)\s*\|[^{}]*\}\}", re.IGNORECASE)
# {{SpoilH|N}} is the wiki's own curated "spoiler-free through book N" marker.
RE_SPOILH = re.compile(r"\{\{\s*SpoilH\s*\|\s*(\d+)\s*\}\}", re.IGNORECASE)
RE_BLOCKQUOTE = re.compile(r"<blockquote>(.*?)</blockquote>", re.DOTALL | re.IGNORECASE)
RE_PARA = re.compile(r"<p>(.*?)</p>", re.DOTALL | re.IGNORECASE)
# The {{Achievement|...}} infobox, e.g. "| reward = Celestial [[Predator Box]]".
RE_ACHIEVEMENT_BOX = re.compile(r"\{\{\s*Achievement\b(.*?)\n\}\}", re.DOTALL | re.IGNORECASE)
RE_BOX_REWARD = re.compile(r"^\s*\|\s*reward\s*=\s*(.+)$", re.IGNORECASE | re.MULTILINE)
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
    # Inline HTML that survives inside a <blockquote>/{{quote}} body: <br>
    # becomes a line break, everything else (<small>, <i>, ...) just unwraps.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^>]*)?>", "", text)
    text = RE_WS.sub(" ", text)
    text = RE_BLANKS.sub("\n\n", text)
    return text.strip()


def _first_positional_param(text: str) -> str:
    """Text up to the first template-level '|' (the boundary before a second
    positional or named param), ignoring '|' inside a [[wikilink|display]]."""
    depth = 0
    i = 0
    while i < len(text) - 1:
        pair = text[i : i + 2]
        if pair == "[[":
            depth += 1
            i += 2
            continue
        if pair == "]]":
            depth = max(0, depth - 1)
            i += 2
            continue
        if text[i] == "|" and depth == 0:
            return text[:i]
        i += 1
    return text


def extract_quote_block(wikitext: str) -> tuple[str, str]:
    """Pull the System AI text out. Returns (text, strategy_used)."""
    # A quote often contains its own {{cite|..}}/{{ref|..}} citation. Strip
    # those first so the naive non-greedy regexes below don't stop at the
    # citation's own "}}" instead of the outer template/tag's.
    wikitext = RE_CITE_INLINE.sub("", wikitext)

    # 1. An HTML <blockquote> of <p> lines - the actual "AI Description"
    #    format most achievement pages use. Checked before the {{quote|..}}
    #    template below: many pages ALSO open with a {{Quote|..}} book
    #    epigraph (attributed to a character, e.g. "|Rory" or "<small>Carl</small>")
    #    that looks like a match but isn't the achievement/monster's own text.
    bq = RE_BLOCKQUOTE.search(wikitext)
    if bq:
        paras = RE_PARA.findall(bq.group(1)) or [bq.group(1)]
        cleaned = strip_markup("\n".join(paras))
        if len(cleaned) > 40:
            return cleaned, "blockquote"

    # 2. A quote template - fallback for the minority of pages with no
    #    <blockquote> at all.
    match = re.search(
        r"\{\{\s*(?:quote|Quote|blockquote|AI|System)\s*\|(.+?)\}\}",
        wikitext,
        re.DOTALL,
    )
    if match:
        body = match.group(1)
        # Drop a leading named first param (quote = ...) and any trailing
        # named or positional params (|author=..., |[[Rory]]) - but not a
        # '|' inside a [[wikilink|display]] within the quote text itself.
        body = re.sub(r"^\s*quote\s*=\s*", "", body, flags=re.IGNORECASE)
        body = _first_positional_param(body)
        cleaned = strip_markup(body)
        if len(cleaned) > 40:
            return cleaned, "template"

    # 3. A leading indented block (": " lines) before the first heading.
    head = RE_HEADING.split(wikitext)[0]
    indented = [ln[1:].strip() for ln in head.splitlines() if ln.startswith(":")]
    if indented:
        cleaned = strip_markup("\n".join(indented))
        if len(cleaned) > 40:
            return cleaned, "indent"

    # 4. Whatever prose sits before the first heading.
    cleaned = strip_markup(head)
    if len(cleaned) > 40:
        return cleaned, "lead"

    return "", "none"


def extract_infobox_reward(wikitext: str) -> str | None:
    """The {{Achievement|...|reward=...}} infobox field - cleaner and more
    reliable than scraping a "Reward:" line out of joke-y AI-voice prose."""
    box = RE_ACHIEVEMENT_BOX.search(wikitext)
    if not box:
        return None
    match = RE_BOX_REWARD.search(box.group(1))
    if not match:
        return None
    cleaned = strip_markup(match.group(1).strip())
    return cleaned or None


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
    """Returns (tier, signal, floor).

    Three signals, most trusted first:
      1. SpoilH   - the wiki's own curated "spoiler-free through book N" marker.
      2. citation - spelled-out book title (rare) or {{cite|N|..}}/{{ref|N|..}}
                    template (common); the lowest-numbered book cited is taken
                    as first appearance.
      3. floor    - [[Category:Floor N]] mapped to a book via config/books.json.

    SpoilH and citation occasionally disagree (SpoilH accounts for
    foreshadowing/recap citations that land in an earlier book than the
    content it describes). When both are present this takes the higher
    (more cautious) of the two rather than picking one source outright -
    for a spoiler filter, safe-but-late beats early-but-wrong.
    """
    spoilh_match = RE_SPOILH.search(wikitext)
    spoilh_tier = int(spoilh_match.group(1)) if spoilh_match else None

    cited = {idx for pattern, idx in citation_patterns if pattern.search(wikitext)}
    cited |= {int(n) for n in RE_CITE_TEMPLATE.findall(wikitext)}
    citation_tier = min(cited) if cited else None

    floors = {int(m) for m in RE_FLOOR_CAT.findall(wikitext)}
    floor = min(floors) if floors else None
    floor_tier = floor_map.get(floor) if floor is not None else None

    if spoilh_tier is not None or citation_tier is not None:
        tier = max(t for t in (spoilh_tier, citation_tier) if t is not None)
        signal = "spoilh" if spoilh_tier is not None else "citation"
        return tier, signal, floor
    if floor_tier is not None:
        return floor_tier, "floor", floor
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
    stats = {"spoilh": 0, "citation": 0, "floor": 0, "none": 0, "no_body": 0, "total": 0}

    for path in sorted(src_dir.glob("*.wikitext")):
        wikitext = path.read_text(encoding="utf-8")
        raw_title = titles.get(path.stem, path.stem.replace("_", " "))

        # Index pages ("Floor 3 Achievements") are navigation, not entries.
        if RE_FLOOR_INDEX_TITLE.fullmatch(raw_title.strip()):
            continue
        # "Achievement", "Boss", etc: the category's own mechanic-overview page.
        if raw_title.strip() in META_PAGE_TITLES.get(kind, ()):
            continue
        # A wiki redirect stub, e.g. "#REDIRECT [[Clurichaun#...]]" - no content
        # of its own, and its target is already indexed under its own title.
        if RE_REDIRECT.match(wikitext):
            continue

        body, strategy = extract_quote_block(wikitext)
        tier, signal, floor = resolve_tier(wikitext, citation_patterns, floor_map)

        # Prefer the structured {{Achievement|...|reward=...}} infobox field;
        # fall back to scraping a "Reward:" line out of the AI-voice prose,
        # which is joke-y and less reliable ("Reward: Nothing! ...Just kidding").
        reward = extract_infobox_reward(wikitext)
        reward_match = RE_REWARD.search(body) or RE_REWARD.search(strip_markup(wikitext))
        if not reward and reward_match:
            reward = reward_match.group(1).strip()
        if reward_match:
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
                f"tier by spoilh {stats['spoilh']}, citation {stats['citation']}, "
                f"floor {stats['floor']}, unresolved {stats['none']} | "
                f"missing body {stats['no_body']}"
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

    # Mirror into web/ so `python3 -m http.server` in that folder just works.
    web_copy = REPO_ROOT / "web" / "entries.json"
    if web_copy.parent.exists():
        web_copy.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"\nwrote {out} - {len(kept)} entries ({spread})")
    print(f"mirrored -> {web_copy}")
    if len(kept) < 60:
        print("WARNING: thin dataset. A daily app wants 150+ or it repeats fast.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
