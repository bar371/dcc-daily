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
    entries, stats = bd.build_kind("achievements", config, verbose=False, image_urls={})
    by_title = {e["title"]: e for e in entries}
    fails = []

    def check(label, got, want):
        if got != want:
            fails.append(f"{label}: got {got!r}, want {want!r}")

    # {{cite|N|..}} template citation, and the EARLIEST cited book wins (B1, not B3).
    ym = by_title["You Monster!"]
    check("You Monster tier", ym["spoilerTier"], 1)
    check("You Monster signal", ym["tierSignal"], "citation")
    check("You Monster body source", ym["bodySource"], "blockquote")
    if "cite" in ym["body"] or "{{" in ym["body"]:
        fails.append("You Monster body: template markup leaked into body text")
    if "New achievement!" not in ym["body"]:
        fails.append("You Monster body: System AI text missing")
    if not ym["reward"] or "Bronze Loot Box" not in ym["reward"]:
        fails.append(f"You Monster reward not extracted from infobox: {ym['reward']!r}")

    # No citation or SpoilH -> fall back to Floor 6 -> Book 5.
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

    # SpoilH (5) disagrees with the lone early citation (2) -> take the safer, higher tier.
    cr = by_title["Cautious Reveal"]
    check("Cautious Reveal tier", cr["spoilerTier"], 5)
    check("Cautious Reveal signal", cr["tierSignal"], "spoilh")

    # Infobox closes on the same line as its last field (no "\n}}"), and
    # {{PAGENAME}} is nested inside an earlier field - regression test for a
    # bug where the reward extractor either missed the box entirely (falling
    # back to messy AI-voice prose) or stopped at PAGENAME's own "}}".
    dp = by_title["Dungeonpreneur"]
    check("Dungeonpreneur reward", dp["reward"], "Royalties (minus taxes)")

    # Blank "|reward=" field must fall through to the prose "Reward:" line,
    # not swallow the next infobox field's value - \s* after "=" matches
    # newlines, so an earlier version of the regex read "|image1=" instead.
    mg = by_title["Menagerie"]
    if not mg["reward"] or "|" in mg["reward"] or "image1" in mg["reward"]:
        fails.append(f"Menagerie reward leaked infobox syntax: {mg['reward']!r}")
    check("Menagerie reward", mg["reward"], "You have a key. It opens only one cage.")

    # A bare infobox placeholder ("None", "Nothing", ...) isn't a real reward
    # - fall through to the AI-voice prose, which has the actual joke text.
    pr = by_title["Placeholder Reward"]
    check("Placeholder Reward reward", pr["reward"], "Well, if there's a heaven, maybe they'll let you in. Because you about to meet your maker.")

    # Book 1's alias ("Dungeon Crawler Carl") is a literal substring of every
    # other book's full bibliographic subtitle ("...: Dungeon Crawler Carl
    # Book 6"). Regression test: citing Book 6 that way must not also tag
    # this Book 1 - no SpoilH here, so a false positive would leak straight
    # through as the final tier.
    cs = by_title["Citation Subtitle"]
    check("Citation Subtitle tier", cs["spoilerTier"], 6)
    check("Citation Subtitle signal", cs["tierSignal"], "citation")

    # Same collision, but via a fan-art filename inside a <gallery> block
    # rather than a citation footnote.
    gf = by_title["Gallery Filename"]
    check("Gallery Filename tier", gf["spoilerTier"], 6)

    # ==Description== is wiki-authored lore prose, separate from the
    # ==AI Description== blockquote already captured in "body" - must not
    # be confused with it, and must stop at the next heading (not leak
    # into ==Trivia==).
    wl = by_title["Wiki Lore"]
    if not wl["description"] or "third person" not in wl["description"]:
        fails.append(f"Wiki Lore description not extracted: {wl['description']!r}")
    if wl["description"] and "nobody reads" in wl["description"]:
        fails.append("Wiki Lore description: AI Description blockquote leaked in")
    if wl["description"] and "must not leak" in wl["description"]:
        fails.append("Wiki Lore description: Trivia section leaked in")

    # No ==Description== heading on this fixture -> field stays absent.
    check("You Monster description", ym["description"], None)

    check("stats total", stats["total"], 10)

    # extract_primary_image() edge cases, tested directly since build_kind()
    # only wires an "image" onto an entry when fetch_images.py's URL cache
    # (network-fetched, not available in this offline test) already has the
    # filename - these exercise the filename/credit parsing on its own.

    # Box closes same-line as |image1= (trailing "}}" on the filename).
    img = bd.extract_primary_image(
        "{{Achievement\n|title1= {{PAGENAME}}\n|image1=Shopping Cart.jpg}}\nbody text"
    )
    check("image same-line box close", img and img["file"], "Shopping Cart.jpg")

    # Bare "File:" prefix with no [[ ]] wikilink brackets.
    img = bd.extract_primary_image("{{Achievement\n|image1 = File:Cover.jpg\n}}\nbody")
    check("image bare File: prefix", img and img["file"], "Cover.jpg")

    # A full [[File:...|thumb|...]] wikilink written directly into the field.
    img = bd.extract_primary_image(
        "{{Achievement\n|image1=[[File:Hadji (1964).png|thumb|Hadji from Jonny Quest]]\n}}\nbody"
    )
    check("image wikilink-in-field", img and img["file"], "Hadji (1964).png")

    # Blank infobox image field -> falls back to the first <gallery> entry,
    # not the second field's value (same \s*-crosses-newlines risk as reward).
    img = bd.extract_primary_image(
        "{{Achievement\n|image1=\n|floor=[[First Floor]]\n}}\nbody\n"
        "<gallery>\nFile:Real Art.jpg|Art by someone\n</gallery>"
    )
    check("image blank field falls to gallery", img and img["file"], "Real Art.jpg")
    check("image gallery credit", img and img["credit"], "Art by someone")

    # No image field and no gallery -> no fabricated image.
    img = bd.extract_primary_image("{{Achievement\n|floor=[[First Floor]]\n}}\nno pictures here")
    check("image absent stays absent", img, None)

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
