#!/usr/bin/env python3
"""Exercise fetch_wiki.py against a stubbed API. No network.

This does NOT prove the real wiki returns what we expect. It proves the code
paths run: continuation, 50-title batching, missing pages, retry/backoff,
slot extraction. Everything except the actual HTTP contract.
"""
import io, json, sys, tempfile, urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import fetch_wiki as fw  # noqa: E402

fw.THROTTLE = 0  # don't actually sleep through the tests

fails = []
def check(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")

def fake_response(payload):
    return io.BytesIO(json.dumps(payload).encode())

# --- categorymembers follows continuation -----------------------------------
pages = [
    {"query": {"categorymembers": [{"title": "A Achievement"}, {"title": "B Achievement"}]},
     "continue": {"cmcontinue": "page|2"}},
    {"query": {"categorymembers": [{"title": "C Achievement"}]}},
]
calls = []
def urlopen_paged(req, timeout=None):
    calls.append(req.full_url)
    return fake_response(pages[len(calls) - 1])

with mock.patch("urllib.request.urlopen", urlopen_paged):
    titles = fw.category_members("Category:Achievements")
check("continuation titles", titles, ["A Achievement", "B Achievement", "C Achievement"])
check("continuation requests", len(calls), 2)
if "cmcontinue=page%7C2" not in calls[1]:
    fails.append("second request did not pass cmcontinue")
if "User-Agent" not in str(fw.USER_AGENT) and not fw.USER_AGENT:
    fails.append("no User-Agent set")

# --- wikitext batching at 50, missing pages skipped -------------------------
many = [f"T{i}" for i in range(120)]
batch_sizes = []
def urlopen_batched(req, timeout=None):
    url = req.full_url
    n = url.count("%7C") + 1  # pipe-separated titles
    batch_sizes.append(n)
    return fake_response({"query": {"pages": [
        {"title": "T0", "revisions": [{"slots": {"main": {"content": "body-0"}}}]},
        {"title": "T1", "missing": True},
        {"title": "T2", "revisions": []},
    ]}})

with mock.patch("urllib.request.urlopen", urlopen_batched):
    out = fw.fetch_wikitext(many)
check("batch sizes", batch_sizes, [50, 50, 20])
check("missing/empty pages skipped", sorted(out), ["T0"])
check("content unwrapped from slots", out["T0"], "body-0")

# --- retries then succeeds --------------------------------------------------
attempts = {"n": 0}
def urlopen_flaky(req, timeout=None):
    attempts["n"] += 1
    if attempts["n"] < 3:
        raise urllib.error.URLError("boom")
    return fake_response({"query": {"categorymembers": []}})

with mock.patch("urllib.request.urlopen", urlopen_flaky), mock.patch("time.sleep"):
    fw.category_members("Category:X")
check("retried before succeeding", attempts["n"], 3)

# --- API-level error is raised, not silently swallowed ----------------------
with mock.patch("urllib.request.urlopen",
                lambda req, timeout=None: fake_response({"error": {"code": "readapidenied"}})), \
     mock.patch("time.sleep"):
    try:
        fw.category_members("Category:X")
        fails.append("API error was swallowed instead of raised")
    except RuntimeError:
        pass

# --- slug() survives the titles the wiki actually has -----------------------
for raw in ["You Monster! Achievement", "Hey Larry, can I borrow your chainsaw? Achievement",
            "Ménage à Quatro Achievement", "You've Killed a Mob! Achievement"]:
    s = fw.slug(raw)
    if not s or "/" in s or len(s) > 120:
        fails.append(f"bad slug for {raw!r}: {s!r}")
check("slug: punctuation-only differences stay distinct",
      len({fw.slug("A! Achievement"), fw.slug("A? Achievement")}), 2)

# Real titles pulled from the live Category:Achievements page.
real = ["You Call That a Trap? Achievement", "You Monster! Achievement",
        "Ménage à Quatro Achievement", "Uh oh. It talks. Achievement",
        "You've Killed a Mob! Achievement", "You've Killed a Mob a Higher Level than Yourself! Achievement",
        "Hey Larry, can I borrow your chainsaw? Achievement", "Janet Jackson\u2019s Nipple Achievement"]
check("slug: no collisions across real titles", len({fw.slug(t) for t in real}), len(real))
for t in real:
    s_ = fw.slug(t)
    if not s_ or "/" in s_ or "\\" in s_ or len(s_) > 120:
        fails.append(f"unsafe slug for {t!r}: {s_!r}")

if fails:
    print("FAIL")
    for f in fails:
        print("  -", f)
    raise SystemExit(1)
print("PASS - fetch_wiki: continuation, batching, retry, error surfacing, slugs")
