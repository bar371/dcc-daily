# Attribution and licensing

## Wiki content
Entry text is derived from the **Dungeon Crawler Carl Wiki** on Fandom,
licensed **CC BY-SA 3.0**. Every entry in the app links back to its source
page, and the about screen carries the licence notice. If you redistribute
this dataset, it stays CC BY-SA.

## The bit that actually constrains you
Much of the achievement text on the wiki is **verbatim System AI prose quoted
from the novels**. That text is Matt Dinniman's copyright. Fandom's CC BY-SA
covers what wiki editors wrote; it cannot re-license quoted book passages.

Practical consequence:

- **Personal / sideloaded build** — fine. Same as keeping quotes in a notes app.
- **Play Store or App Store** — not fine. Publishing an app whose whole
  function is serving up an author's prose invites a takedown, and deservedly.

If you ever want this public, the route is to ask Dinniman, or to ship only
wiki-editor-written summaries rather than the quoted text. The scraper keeps
`body` and `sourceUrl` separate precisely so that swap stays possible.

## Code
Repo code: MIT. Not affiliated with or endorsed by Matt Dinniman, Dandy House,
Ace, Soundbooth Theater, or Fandom.
