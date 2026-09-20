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
| 3. **Web app (PWA)** | **Built**, picker tested, runs on placeholder data |
| 4. Notifications | See `docs/deploy.md` — the web has no local scheduler |
| 5. Deploy | Workflow written, see `docs/deploy.md` |
| 6. Refresh automation | Workflow written |

The web app replaced the Flutter plan. Same install-to-home-screen result on
both phones, no app stores, no $99/yr Apple fee, one codebase. The only thing
it gives up is locally scheduled notifications.

Full breakdown in [`PLAN.md`](PLAN.md).

## Getting real data into it

Nothing to install. Push the repo, then **Actions → publish → Run workflow**
with **include_data** ticked. The runner scrapes the wiki, validates the
result, and deploys. Details and other hosts in [`docs/deploy.md`](docs/deploy.md).

Until that runs, the site shows placeholder cards and says so.

## Running it locally

No dependencies. Python 3.9+.

    python3 tools/test_parse.py              # parser, offline
    python3 tools/test_fetch.py              # fetcher against a mocked API
    node web/test_picker.js                  # daily-pick algorithm
    cd web && python3 -m http.server 8000    # serve it
    python3 tools/fetch_wiki.py              # ~3 min, caches to raw/
    python3 tools/build_dataset.py --report  # -> data/entries.json



## Layout

    config/books.json    book/floor table driving the spoiler filter
    tools/fetch_wiki.py  MediaWiki client, caches raw wikitext
    tools/build_dataset.py  wikitext -> data/entries.json
    tools/test_parse.py  fixture tests, no network
    docs/spoilers.md     how tiers are assigned, and what to verify
    web/                 the PWA - open web/index.html, or see docs/deploy.md
    docs/deploy.md       hosting options, install steps, notification reality
    NOTICE.md            attribution and the copyright constraint
