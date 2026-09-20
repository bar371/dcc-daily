# dcc-daily

A daily Dungeon Crawler Carl achievement, on your phone, filtered so it can't
spoil a book you haven't read yet.

Pick how far you've got. Every morning you get one System AI achievement drawn
only from the books you've finished. No ads, no accounts, no network required.

    ┌─────────────────────────────────┐
    │  NEW ACHIEVEMENT!               │
    │  You Monster!                   │
    │                                 │
    │  You have killed an infant! An  │
    │  infant! Okay, okay. Unless     │
    │  you're a complete psychopath…  │
    │                                 │
    │  Reward: That was your reward.  │
    │  It was also a lie.             │
    └─────────────────────────────────┘

## Status

| Phase | State |
|---|---|
| 1. Data pipeline | **Written**, two test suites passing — but see *What is and isn't tested* |
| 2. Dataset curation | Blocked on your Phase 1 run |
| 3. Flutter app | Not started |
| 4. Notifications | Not started |
| 5. Build + install | Not started |
| 6. Refresh automation | Workflow written |

Full breakdown in [`PLAN.md`](PLAN.md).

## Quick start

No dependencies. Python 3.9+.

    python3 tools/test_parse.py              # parser, offline
    python3 tools/test_fetch.py              # fetcher against a mocked API
    python3 tools/fetch_wiki.py              # ~3 min, caches to raw/
    python3 tools/build_dataset.py --report  # -> data/entries.json

## What is and isn't tested

Be clear-eyed about this before trusting the output.

**Tested, really:**
- Parser logic — tier resolution (citation > floor > unresolved), reward
  extraction, markup stripping. Caught one real bug: rewards inside
  `{{Quote}}` templates were stripped before extraction.
- Fetcher code paths against a mocked API — continuation, 50-title batching,
  missing-page skipping, retry/backoff, API errors surfacing not swallowing.
- `slug()` against all 150 real achievement titles scraped from the live
  category page. Zero collisions, zero truncation.

**Not tested, at all:**
- A single real HTTP request to the wiki. The build environment had no route
  to fandom.com.
- The parser against real wikitext. The fixtures in `tools/fixtures/` are
  *invented* — written by the same hand as the regex they exercise. They prove
  the parser is self-consistent, not that it matches how the wiki is written.
  Expect the first live run to mis-parse pages.
- Both CI workflows.
- Anything Flutter. Nothing exists.

The `--report` flag on `build_dataset.py` exists for exactly this reason.

## Layout

    config/books.json    book/floor table driving the spoiler filter
    tools/fetch_wiki.py  MediaWiki client, caches raw wikitext
    tools/build_dataset.py  wikitext -> data/entries.json
    tools/test_parse.py  fixture tests, no network
    docs/spoilers.md     how tiers are assigned, and what to verify
    app/                 Flutter app (phase 3)
    NOTICE.md            attribution and the copyright constraint

## Read this before publishing anywhere

Achievement text is largely Matt Dinniman's prose quoted on the wiki. Fine on
your own phone, not fine on an app store. See [`NOTICE.md`](NOTICE.md).
