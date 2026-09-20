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

## Artwork
Some entries carry a lead image pulled from the wiki's infobox or gallery.
These are almost all **individual fan art** - credited to a Reddit/Instagram/
Bluesky handle or a small studio, not Fandom or Dinniman - plus a couple of
press photos the wiki itself claims fair use on for commentary.

The app never downloads or rehosts the image files. `tools/fetch_images.py`
resolves each filename to Fandom's own CDN URL via the MediaWiki API and
stores *that URL plus the credited artist*, nothing else; `web/app.js`
hotlinks it, same as your browser does when you visit the wiki page, and
shows the credit as a link back to the wiki's file page. Copying the pixels
into this repo would go a step further than that and isn't done here.

If an artist wants their work out of this app, dropping the filename from
`raw/image_urls.json` (or fixing/removing the source page's `image1=` field
before the next `fetch_wiki.py` run) is enough - there's no separate copy to
also delete.

## Code
Repo code: MIT. Not affiliated with or endorsed by Matt Dinniman, Dandy House,
Ace, Soundbooth Theater, or Fandom.
