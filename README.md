# dcc-daily

A daily Dungeon Crawler Carl achievement, on your phone, filtered so it can't
spoil a book you haven't read yet.

Pick how far you've got. Every morning you get one System AI achievement drawn
only from the books you've finished. No ads, no accounts.

**Live:** https://bar371.github.io/dcc-daily/ — install via "Add to Home
Screen" (Safari on iOS, Chrome on Android).

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
| 1. Data pipeline | **Done.** Run against the live wiki: 280 entries, 0% unresolved achievement tiers. |
| 2. Dataset curation | **Open.** `config/books.json`'s floor→book ranges are still `"verified": false` — nobody's spot-checked them against the actual novels yet. See `docs/spoilers.md`. |
| 3. **Web app (PWA)** | **Built and deployed**, picker tested, live with real data. |
| 4. Notifications | See `docs/deploy.md` — the web has no local scheduler |
| 5. Deploy | **Live** on GitHub Pages, public, with real data. |
| 6. Refresh automation | Workflow runs monthly, but ships placeholder data on that schedule by default — a real refresh needs a manual **Actions → publish → Run workflow** with `include_data` ticked. |

The web app replaced the Flutter plan. Same install-to-home-screen result on
both phones, no app stores, no $99/yr Apple fee, one codebase. The only thing
it gives up is locally scheduled notifications.

## Refreshing the data

**Actions → publish → Run workflow**, tick **include_data**. The runner
scrapes the wiki, validates the result, and deploys. Details and other hosts
in [`docs/deploy.md`](docs/deploy.md).

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
