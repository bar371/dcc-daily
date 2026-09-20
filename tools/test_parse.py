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

    check("stats total", stats["total"], 3)

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
