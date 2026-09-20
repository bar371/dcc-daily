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
| 1. Data pipeline | **Done**, tests passing, not yet run against the live wiki |
| 2. Dataset curation | Blocked on your Phase 1 run |
| 3. Flutter app | Not started |
| 4. Notifications | Not started |
| 5. Build + install | Not started |
| 6. Refresh automation | Workflow written |

Full breakdown in [`PLAN.md`](PLAN.md).

## Quick start

No dependencies. Python 3.9+.

    python3 tools/test_parse.py              # verify the parser (offline)
    python3 tools/fetch_wiki.py              # ~3 min, caches to raw/
    python3 tools/build_dataset.py --report  # -> data/entries.json

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
