/* Placeholder data so the page has something to show before you run the
   scraper. Every line below is written from scratch for this demo - none of
   it is text from the books or the wiki, deliberately, because that text is
   Matt Dinniman's copyright.
   Real content arrives as entries.json, which takes precedence over this. */
window.DCC_FALLBACK = {
  version: 0,
  demo: true,
  books: [
    { index: 1, title: "Dungeon Crawler Carl", short: "Book 1" },
    { index: 2, title: "Carl's Doomsday Scenario", short: "Book 2" },
    { index: 3, title: "The Dungeon Anarchist's Cookbook", short: "Book 3" },
    { index: 4, title: "The Gate of the Feral Gods", short: "Book 4" },
    { index: 5, title: "The Butcher's Masquerade", short: "Book 5" },
    { index: 6, title: "The Eye of the Bedlam Bride", short: "Book 6" },
    { index: 7, title: "This Inevitable Ruin", short: "Book 7" },
    { index: 8, title: "Book 8", short: "Book 8" }
  ],
  entries: [
    {
      id: "demo_01", kind: "achievements", spoilerTier: 1, floor: 1,
      title: "Sample Entry",
      body: "This is placeholder text, not a real achievement. It is here so you can see how a card is laid out before the scraper has run.\n\nOnce entries.json is published alongside this page, real entries replace everything on this screen.",
      reward: "Nothing. It is a placeholder. Manage your expectations.",
      sourceUrl: null
    },
    {
      id: "demo_02", kind: "achievements", spoilerTier: 1, floor: 2,
      title: "Long Body Test",
      body: "A second placeholder, deliberately wordier than the first, to check that a paragraph of real length still reads comfortably on a narrow phone screen without the measure running too wide or the display face colliding with the body text below it.",
      reward: "A satisfied feeling about line length.",
      sourceUrl: null
    },
    {
      id: "demo_03", kind: "achievements", spoilerTier: 3, floor: 4,
      title: "Spoiler Gate Test",
      body: "This placeholder is tagged as Book 3. Set your progress to Book 1 or 2 in Settings and it disappears from the pool entirely.\n\nThat is the whole mechanism: an entry is only ever drawn if its tier is at or below the book you have finished.",
      reward: "Confidence that nothing above your setting can reach you.",
      sourceUrl: null
    },
    {
      id: "demo_04", kind: "achievements", spoilerTier: 1, floor: null,
      title: "No Reward Line",
      body: "Some entries have no reward. This one checks that the card closes cleanly when the gold footer is absent.",
      reward: null,
      sourceUrl: null
    }
  ]
};
