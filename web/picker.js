/* Pure daily-pick logic. No DOM, no storage - so it can be tested directly.
   Loaded as a plain script in the browser and required() in tests. */
(function (root) {
  const EPOCH = Date.UTC(2026, 0, 1);

  /* mulberry32: small, fast, seedable, identical across JS engines. */
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffled(items, seed) {
    const out = items.slice();
    const rand = rng(seed);
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }

  /* Local calendar day, so the entry flips at the reader's own midnight. */
  function dayIndex(now) {
    const d = now || new Date();
    const local = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
    return Math.floor((local - EPOCH) / 86400000);
  }

  function pool(entries, finishedBook) {
    return entries
      .filter((e) => typeof e.spoilerTier === "number" && e.spoilerTier <= finishedBook)
      .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }

  function pickFor(entries, finishedBook, seed, day) {
    const items = pool(entries, finishedBook);
    if (!items.length) return null;
    // Reshuffle once per full pass: nothing repeats until the pool is exhausted.
    const cycle = Math.floor(day / items.length);
    const order = shuffled(items, (seed ^ Math.imul(cycle, 2654435761)) >>> 0);
    return order[((day % items.length) + items.length) % items.length];
  }

  const api = { EPOCH, rng, shuffled, dayIndex, pool, pickFor };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DCCPicker = api;
})(typeof self !== "undefined" ? self : globalThis);
