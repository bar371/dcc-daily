# Implementation plan

Six phases. Each ends with something you can actually run.

---

## Phase 0 — decisions locked

| Question | Answer | Why |
|---|---|---|
| Stack | **Flutter** | One codebase, Android + iOS, good local-notification story, no JS toolchain |
| Backend | **None** | Dataset is ~200 entries of text. Ships in the app bundle. Nothing to host, nothing to pay for, works on a plane |
| Daily pick | **Deterministic, on-device** | Seeded shuffle. No server needed and no repeats until the pool is exhausted |
| Dataset refresh | **Optional pull from GitHub Pages** | App works offline forever; checks for a newer `entries.json` weekly if online |
| Distribution | **Sideload** | See `NOTICE.md`. Store publication is a copyright problem, not a technical one |
| Ads / tracking / accounts | **None** | Stated requirement |

**Why not React Native / Expo:** Expo + EAS would let you build iOS without a
Mac, which is a real advantage. But you still need a $99/yr Apple Developer
account for anything beyond a 7-day sideload, so it doesn't dodge the actual
cost. Flutter wins on the offline-first, notification-heavy shape of this app.
If you'd rather have Expo, say so at Phase 3 — phases 1-2 are unaffected.

---

## Phase 1 — data pipeline ✅ done

Built and tested in this repo.

- `tools/fetch_wiki.py` — MediaWiki API client, stdlib only, caches to `raw/`
- `tools/build_dataset.py` — wikitext → `data/entries.json`, assigns spoiler tiers
- `tools/test_parse.py` — fixture tests, no network, currently passing
- `config/books.json` — book/floor table driving the filter

**What it does not do:** it has never run against the live wiki. I had no
network access to fandom.com. The parser is built defensively with three
extraction strategies and a `--report` mode, but the first real run will
surface pages it mis-parses.

**Your next action:**

```bash
python3 tools/fetch_wiki.py          # ~3 min, polite 1 req/sec
python3 tools/build_dataset.py --report
```

Then paste the report back and I'll tighten the parser against real pages.

**Exit criteria:** 150+ entries, fewer than 10% unresolved tiers, and the
floor ranges in `config/books.json` verified by you (see `docs/spoilers.md`).

---

## Phase 2 — dataset curation

Not glamorous, matters most.

1. Verify floor→book ranges. Flip `"verified": true`.
2. Spot-check 20 random entries against what you remember. Any entry tagged a
   book *later* than where you actually met it is a spoiler leak.
3. Decide on monsters. Achievements are self-contained jokes and carry the
   app on their own. Monster pages are descriptive wiki prose — less punchy,
   more spoilery. **Recommendation: ship achievements-only in v1**, add
   monsters behind a toggle later.
4. Drop entries whose body is under ~80 characters. They read as broken.

**Exit criteria:** `data/entries.json` you'd trust not to spoil you.

---

## Phase 3 — web app (PWA) ✅ built

**Replaced the Flutter plan.** A PWA installs to the home screen on both
phones, works offline, costs nothing, needs no app store, and skips the
$99/yr Apple developer fee. It gives up exactly one thing: locally scheduled
notifications. See `docs/deploy.md` for what to do about that.

```
web/
├── index.html            shell
├── styles.css            System AI broadcast styling
├── picker.js             pure daily-pick logic (tested)
├── app.js                rendering + settings
├── sw.js                 offline cache
├── manifest.webmanifest  home-screen install
└── entries-fallback.js   placeholder data, original text
```

Deploy with `.github/workflows/pages.yml`, or per `docs/deploy.md`.

**Still to do:** generate `icon-192.png`, `icon-512.png`, `icon-180.png` from
`icon.svg`. Verify the layout in a real browser. Confirm offline works after
a hard reload with the network off.

---

## Phase 3b — Flutter app (only if you want real notifications)

```
app/lib/
├── main.dart
├── models/entry.dart              # Entry, Book, Dataset
├── data/dataset_repository.dart   # load bundled JSON, optional remote refresh
├── data/settings_store.dart       # shared_preferences: finishedBook, seed, time
├── logic/daily_picker.dart        # the algorithm below
├── ui/today_screen.dart           # the card
├── ui/history_screen.dart         # past picks, favourites
├── ui/settings_screen.dart        # book slider, notification time, about
└── ui/theme.dart                  # System AI notification styling
```

**The daily pick.** No server, no repeats, stable across restarts:

```dart
// Per-install random seed, generated once, stored in prefs.
// Filter to the readable pool, shuffle deterministically, index by day count.
final pool = entries.where((e) => e.spoilerTier <= finishedBook).toList()
  ..sort((a, b) => a.id.compareTo(b.id));           // stable base order
final epochDay = today.difference(DateTime.utc(2026, 1, 1)).inDays;
final cycle = epochDay ~/ pool.length;               // reshuffle each full pass
pool.shuffle(Random(installSeed ^ cycle));
final todays = pool[epochDay % pool.length];
```

Properties worth having: same entry all day, no repeat until the pool is
exhausted, different for every install, no network, and raising your book
progress mid-cycle reshuffles cleanly instead of crashing.

**Exit criteria:** app runs in an emulator, shows today's entry, book slider
changes the pool, survives a restart.

---

## Phase 4 — notification and polish

- `flutter_local_notifications` + `timezone`, daily at a user-set time
- Android 13+ `POST_NOTIFICATIONS` runtime permission; iOS provisional auth
- Notification body = the entry title only. The joke should need a tap
- Share as image, favourite/star, history list
- Styling: the System AI's blue notification box. Monospace-ish display face,
  hard edges, no rounded-corner Material softness

**Exit criteria:** notification fires at the right local time after a reboot.

---

## Phase 5 — build and install

**Android** — free. GitHub Actions builds a signed APK on tag:

```bash
git tag v0.1.0 && git push --tags     # workflow attaches the APK to a release
```

**iOS** — costs money or patience:
- Free: Xcode on a Mac, 7-day sideload, re-sign weekly. Fine for one phone.
- $99/yr: Apple Developer, TestFlight, 90-day builds, installs on your family's
  phones too.

There is no third option. If you don't have a Mac and don't want to pay, ship
Android and revisit.

**Exit criteria:** it's on your phone and it buzzed at 08:00.

---

## Phase 6 — keeping it fed

`.github/workflows/scrape.yml` runs monthly, re-scrapes, and opens a PR if
`entries.json` changed. You review the diff — which doubles as spoiler review
when a new book lands — and merge. The app pulls the updated file on next launch.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Copyright on quoted prose | Kills store distribution | Sideload only. `NOTICE.md` |
| Wrong floor→book mapping | **Spoils a book** | Phase 2 manual verification; `unknownTierPolicy: hide` |
| Wiki markup varies per page | Mangled entries | 3 extraction strategies, `--report`, fixture tests |
| Pool too small at Book 1 | Repeats within weeks | Count per tier in Phase 1; if thin, seed from `Floor 1/2` index pages |
| Fandom blocks the scraper | Pipeline dies | 1 req/sec, real User-Agent, aggressive caching. Runs monthly, not daily |
