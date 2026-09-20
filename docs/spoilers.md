# The spoiler filter

The whole point of the app. Get this wrong and you ruin a book for yourself.

## How a tier is decided

`build_dataset.py` assigns each entry a `spoilerTier` (1-8) from three signals:

| Signal | How | Trust |
|---|---|---|
| `citation` | Page cites a book by name in a `<ref>`. Lowest-numbered book cited wins. | High |
| `floor` | Page is in `Category:Floor N Achievements`; floors map to books via `config/books.json`. | Medium |
| `none` | Neither. Falls back to `unknownTierPolicy`. | — |

Citation beats floor, because a "Floor 6 Achievement" first *mentioned* in
Book 3 is a Book 3 spoiler, not a Book 5 one.

## The app rule

Show an entry only if `entry.spoilerTier <= user.finishedBook`.

Default `unknownTierPolicy` is `hide`. A smaller safe dataset beats a bigger
one that spoils Book 7. Change it in `config/books.json` if you'd rather see
everything.

## Before first release: verify the floor ranges

Every book in `config/books.json` has `"verified": false`. The floor ranges are
a best guess from publisher blurbs, not from reading. You've read the books —
check them and flip the flag. Specifically worth your eye:

- Book 1 covering the tutorial plus floors 1-2
- Book 6 (`The Eye of the Bedlam Bride`) mapped to floors 7-8
- Book 8's real title and floor

A wrong range silently leaks spoilers one book early, which is the one failure
mode that actually matters here. Audit with:

    python3 tools/build_dataset.py --report

## Checking your work

    python3 -c "
    import json
    d = json.load(open('data/entries.json'))
    for b in d['books']:
        n = sum(1 for e in d['entries'] if e['spoilerTier'] <= b['index'])
        print(f\"finished {b['short']}: {n} entries available\")
    "

If Book 1 gives you fewer than ~20, the filter is too tight and the app will
feel empty on day one.
