#!/usr/bin/env python3
"""Run the parser against fixtures. No network, no deps: python3 tools/test_parse.py"""
import json, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_dataset as bd  # noqa: E402

def run():
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "tools" / "fixtures" / "achievements", tmp / "achievements")
    shutil.copytree(ROOT / "tools" / "fixtures" / "gods", tmp / "gods")
    bd.RAW_DIR = tmp
    config = json.loads((ROOT / "config" / "books.json").read_text())
    entries, stats = bd.build_kind("achievements", config, verbose=False)
    by_title = {e["title"]: e for e in entries}
    fails = []

    def check(label, got, want):
        if got != want:
            fails.append(f"{label}: got {got!r}, want {want!r}")

    # Citation beats floor, and the EARLIEST cited book wins (B1, not B3).
    ym = by_title["You Monster!"]
    check("You Monster tier", ym["spoilerTier"], 1)
    check("You Monster signal", ym["tierSignal"], "citation")
    check("You Monster body source", ym["bodySource"], "template")
    if "Dinniman" in ym["body"]:
        fails.append("You Monster body: citation leaked into body text")
    if "New achievement!" not in ym["body"]:
        fails.append("You Monster body: System AI text missing")

    # No citation -> fall back to Floor 6 -> Book 5.
    sv = by_title["Soft Vore"]
    check("Soft Vore tier", sv["spoilerTier"], 5)
    check("Soft Vore signal", sv["tierSignal"], "floor")
    check("Soft Vore floor", sv["floor"], 6)
    if not sv["reward"] or "Gold Gullet" not in sv["reward"]:
        fails.append(f"Soft Vore reward not extracted: {sv['reward']!r}")

    # Neither signal -> no tier invented.
    mp = by_title["Mystery Page"]
    check("Mystery tier", mp["spoilerTier"], None)
    check("Mystery signal", mp["tierSignal"], "none")

    # External link markup [url text] must become plain text, not leak brackets/URLs.
    pe = by_title["PETA Enthusiast"]
    if "[http" in pe["body"] or "en.wikipedia.org" in pe["body"]:
        fails.append(f"PETA Enthusiast body leaked external link markup: {pe['body']!r}")
    if "Steve Irwin" not in pe["body"]:
        fails.append(f"PETA Enthusiast body lost external link text: {pe['body']!r}")

    check("stats total", stats["total"], 4)

    # "gods" is a separate kind from "achievements" - build_kind() must
    # process it the same way (citation/floor/quote-block extraction all work
    # the same regardless of kind).
    god_entries, god_stats = bd.build_kind("gods", config, verbose=False)
    check("gods stats total", god_stats["total"], 1)
    emberus = god_entries[0]
    check("Emberus kind", emberus["kind"], "gods")
    check("Emberus tier", emberus["spoilerTier"], 4)
    check("Emberus signal", emberus["tierSignal"], "citation")
    if "pledged yourself to Emberus" not in emberus["body"]:
        fails.append(f"Emberus body missing System AI text: {emberus['body']!r}")
    if not emberus["reward"] or "fire resistance" not in emberus["reward"]:
        fails.append(f"Emberus reward not extracted: {emberus['reward']!r}")

    for e in entries:
        if not e["sourceUrl"].startswith("https://"):
            fails.append(f"bad sourceUrl on {e['title']}")
        if not e["id"]:
            fails.append(f"missing id on {e['title']}")

    shutil.rmtree(tmp)
    return fails

if __name__ == "__main__":
    problems = run()
    if problems:
        print("FAIL")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("PASS - parser handles citation, floor, and unresolved tiers")
