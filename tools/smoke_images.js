#!/usr/bin/env node
/* Load card art the way a real browser does, against the assembled site.

   Fandom's image server answers a request whose Referer is another site with
   a 404 placeholder that is still a valid 300px image, so a dataset check or
   an image-width check both pass while every card shows a grey box. This
   checks the actual HTTP status of each image the app requests.

   Usage: node tools/smoke_images.js http://127.0.0.1:8000/ _site/entries.json */
const fs = require("fs");
const { chromium } = require("playwright");

const [base, datasetPath] = process.argv.slice(2);
const dataset = JSON.parse(fs.readFileSync(datasetPath, "utf8"));
const maxBook = Math.max(...dataset.books.map((b) => b.index));

// One card per kind, then fill up to 6 - enough to catch a site-wide break.
const withArt = dataset.entries.filter((e) => e.image && e.image.url);
const sample = [];
for (const kind of new Set(withArt.map((e) => e.kind))) sample.push(withArt.find((e) => e.kind === kind));
for (const e of withArt) if (sample.length < 6 && !sample.includes(e)) sample.push(e);

(async () => {
  if (!sample.length) {
    console.log("::error::no entries with artwork to check");
    process.exit(1);
  }
  const browser = await chromium.launch();
  const failures = [];
  for (const entry of sample) {
    const page = await browser.newPage();
    await page.addInitScript((book) => {
      localStorage.setItem("dccDaily.v1", JSON.stringify({ finishedBook: book, seed: 1 }));
    }, maxBook);
    // A one-entry dataset forces the app to render this card.
    await page.route("**/entries.json*", (route) =>
      route.fulfill({ json: { ...dataset, entries: [entry] } }));
    const image = page.waitForResponse((r) => r.url() === entry.image.url, { timeout: 30000 });
    await page.goto(base, { waitUntil: "load" });
    try {
      const res = await image;
      const type = res.headers()["content-type"] || "";
      if (res.status() !== 200 || !type.startsWith("image/")) {
        failures.push(`${entry.title}: ${res.status()} ${type}`);
      }
    } catch {
      failures.push(`${entry.title}: the app never requested its image`);
    }
    await page.close();
  }
  await browser.close();

  console.log(`checked ${sample.length} cards: ${sample.map((e) => e.title).join(", ")}`);
  if (failures.length) {
    console.log("::error::card artwork failed to load");
    for (const f of failures) console.log(`  - ${f}`);
    process.exit(1);
  }
  console.log("OK: all card artwork loaded");
})();
