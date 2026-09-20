/* node web/test_picker.js - tests the daily-pick algorithm. */
const P = require("./picker.js");

const fails = [];
const check = (label, got, want) => {
  if (got !== want) fails.push(`${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
};

const makeEntries = (n, tier = 1) =>
  Array.from({ length: n }, (_, i) => ({ id: `e${String(i).padStart(3, "0")}`, spoilerTier: tier }));

// --- no repeats within a full cycle -----------------------------------------
{
  const entries = makeEntries(40);
  const seen = [];
  for (let day = 0; day < 40; day++) seen.push(P.pickFor(entries, 1, 12345, day).id);
  check("cycle covers every entry exactly once", new Set(seen).size, 40);
}

// --- a longer run: still no repeat inside any window of pool length ----------
{
  const entries = makeEntries(25);
  const run = [];
  for (let day = 0; day < 250; day++) run.push(P.pickFor(entries, 1, 999, day).id);
  let worst = null;
  for (let i = 0; i + 25 <= run.length; i += 25) {
    const window = new Set(run.slice(i, i + 25));
    if (window.size !== 25) worst = i;
  }
  check("every aligned 25-day window is a full permutation", worst, null);
}

// --- stable: same day always gives the same entry ---------------------------
{
  const entries = makeEntries(30);
  const a = P.pickFor(entries, 1, 777, 100).id;
  const b = P.pickFor(entries, 1, 777, 100).id;
  check("same inputs are deterministic", a, b);
}

// --- consecutive cycles differ (it reshuffles, not just repeats the order) ---
{
  const entries = makeEntries(20);
  const first = Array.from({ length: 20 }, (_, d) => P.pickFor(entries, 1, 42, d).id).join();
  const second = Array.from({ length: 20 }, (_, d) => P.pickFor(entries, 1, 42, d + 20).id).join();
  if (first === second) fails.push("second cycle repeated the first cycle's order verbatim");
}

// --- different seeds give different orders ----------------------------------
{
  const entries = makeEntries(30);
  const a = Array.from({ length: 30 }, (_, d) => P.pickFor(entries, 1, 1, d).id).join();
  const b = Array.from({ length: 30 }, (_, d) => P.pickFor(entries, 1, 2, d).id).join();
  if (a === b) fails.push("two different seeds produced an identical sequence");
}

// --- spoiler filter is a hard gate ------------------------------------------
{
  const entries = [
    ...makeEntries(5, 1),
    ...makeEntries(5, 4).map((e) => ({ ...e, id: "b4" + e.id })),
    ...makeEntries(5, 7).map((e) => ({ ...e, id: "b7" + e.id })),
  ];
  check("book 1 reader sees only tier 1", P.pool(entries, 1).length, 5);
  check("book 4 reader sees tiers 1 and 4", P.pool(entries, 4).length, 10);
  const leaked = Array.from({ length: 200 }, (_, d) => P.pickFor(entries, 4, 5, d))
    .filter((e) => e.spoilerTier > 4).length;
  check("no entry above the reader's book ever surfaces", leaked, 0);
  const untiered = [{ id: "x", spoilerTier: null }, { id: "y" }];
  check("entries with no tier are excluded", P.pool(untiered, 8).length, 0);
}

// --- edge cases -------------------------------------------------------------
{
  check("empty pool returns null", P.pickFor([], 1, 1, 5), null);
  check("single entry pool works", P.pickFor(makeEntries(1), 1, 1, 9999).id, "e000");
  const before = P.pickFor(makeEntries(10), 1, 1, -37);
  if (!before) fails.push("dates before the epoch returned null");
  check("negative day index stays in range", typeof before.id, "string");
}

// --- dayIndex uses the local calendar day, not UTC --------------------------
{
  // 23:30 local on the 2nd must be day 1, even where that is the 3rd in UTC.
  const d = new Date(2026, 0, 2, 23, 30);
  check("dayIndex is local-calendar based", P.dayIndex(d), 1);
  check("epoch day is zero", P.dayIndex(new Date(2026, 0, 1, 0, 1)), 0);
  const a = P.dayIndex(new Date(2026, 0, 5, 0, 5));
  const b = P.dayIndex(new Date(2026, 0, 5, 23, 55));
  check("the index does not change during a day", a, b);
}

// --- raising your book mid-cycle keeps working ------------------------------
{
  const entries = [...makeEntries(8, 1), ...makeEntries(8, 2).map((e) => ({ ...e, id: "t2" + e.id }))];
  const day = 53;
  const atBook1 = P.pickFor(entries, 1, 31337, day);
  const atBook2 = P.pickFor(entries, 2, 31337, day);
  if (!atBook1 || !atBook2) fails.push("pick failed after changing finishedBook");
  check("pool grows when you finish another book", P.pool(entries, 2).length, 16);
}

// --- distribution sanity: no entry wildly over-served -----------------------
{
  const entries = makeEntries(50);
  const counts = {};
  for (let day = 0; day < 5000; day++) {
    const id = P.pickFor(entries, 1, 8675309, day).id;
    counts[id] = (counts[id] || 0) + 1;
  }
  const values = Object.values(counts);
  check("every entry appears over 100 cycles", values.length, 50);
  check("each appears exactly once per cycle", new Set(values).size, 1);
}

if (fails.length) {
  console.log("FAIL");
  fails.forEach((f) => console.log("  -", f));
  process.exit(1);
}
console.log("PASS - picker: no repeats, deterministic, reshuffles, spoiler gate holds, edges safe");
