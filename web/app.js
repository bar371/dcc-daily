/* DCC Daily - deterministic daily pick, offline, no backend. */

const STORE = "dccDaily.v1";
const EPOCH = Date.UTC(2026, 0, 1);

const state = {
  dataset: null,
  settings: load(),
};

function load() {
  const fallback = { finishedBook: 1, seed: null, showUnknown: false };
  try {
    const raw = localStorage.getItem(STORE);
    if (!raw) return { ...fallback, seed: newSeed() };
    const parsed = { ...fallback, ...JSON.parse(raw) };
    if (!parsed.seed) parsed.seed = newSeed();
    return parsed;
  } catch {
    return { ...fallback, seed: newSeed() };
  }
}

function save() {
  try {
    localStorage.setItem(STORE, JSON.stringify(state.settings));
  } catch {
    /* Private mode or quota. The app still works, it just forgets. */
  }
}

function newSeed() {
  const buf = new Uint32Array(1);
  (self.crypto || {}).getRandomValues?.(buf);
  return buf[0] || Math.floor(Math.random() * 2 ** 32);
}

const { dayIndex, pool: poolOf, pickFor: pickEntry } = self.DCCPicker;

function pool() {
  return poolOf(state.dataset.entries, state.settings.finishedBook);
}

function pickFor(day) {
  return pickEntry(state.dataset.entries, state.settings.finishedBook,
                   state.settings.seed, day);
}

/* ---------- rendering ---------- */

function showDemoNotice() {
  const el = $("#notice");
  el.hidden = false;
  el.innerHTML = "";
  const strong = document.createElement("strong");
  strong.textContent = "Showing placeholder data.";
  const rest = document.createElement("span");
  rest.textContent =
    " No entries.json was found, so these cards are samples, not real " +
    "achievements. Run the scraper and deploy the dataset to replace them.";
  el.append(strong, rest);
  if (state.loadError) {
    const why = document.createElement("code");
    why.textContent = state.loadError;
    el.append(document.createElement("br"), why);
  }
}

const $ = (sel) => document.querySelector(sel);

function text(el, value) {
  el.textContent = value;
  return el;
}

function render() {
  const day = dayIndex();
  const entry = pickFor(day);
  const card = $("#card");
  card.innerHTML = "";

  $("#date").textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long", day: "numeric", month: "long",
  });

  if (!entry) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = state.dataset.entries.length
      ? "Nothing unlocked yet. Set how far you've read below."
      : "No entries loaded. Run the scraper and publish entries.json.";
    card.append(p);
    updateCount();
    return;
  }

  const banner = document.createElement("p");
  banner.className = "banner";
  banner.textContent = entry.kind === "monsters" ? "MOB IDENTIFIED" : "NEW ACHIEVEMENT!";

  const name = document.createElement("h1");
  name.className = "name";
  name.textContent = entry.title;

  const body = document.createElement("p");
  body.className = "body-text";
  body.textContent = entry.body;

  card.append(banner, name);

  if (entry.image) {
    const figure = document.createElement("figure");
    figure.className = "art";
    const img = document.createElement("img");
    img.src = entry.image.url;
    img.alt = "";
    img.loading = "lazy";
    figure.append(img);
    if (entry.image.credit) {
      const cap = document.createElement("figcaption");
      if (entry.image.wikiPage) {
        const link = document.createElement("a");
        link.href = entry.image.wikiPage;
        link.rel = "noopener";
        link.target = "_blank";
        link.textContent = entry.image.credit;
        cap.append(link);
      } else {
        cap.textContent = entry.image.credit;
      }
      figure.append(cap);
    }
    card.append(figure);
  }

  card.append(body);

  if (entry.reward) {
    const reward = document.createElement("p");
    reward.className = "reward";
    const label = document.createElement("b");
    label.textContent = "Reward: ";
    reward.append(label, document.createTextNode(entry.reward));
    card.append(reward);
  }

  const meta = document.createElement("p");
  meta.className = "meta";
  const book = state.dataset.books.find((b) => b.index === entry.spoilerTier);
  meta.append(document.createTextNode(book ? book.short : `Book ${entry.spoilerTier}`));
  if (entry.floor != null) meta.append(document.createTextNode(`Floor ${entry.floor}`));
  if (entry.sourceUrl) {
    const link = document.createElement("a");
    link.href = entry.sourceUrl;
    link.rel = "noopener";
    link.target = "_blank";
    link.textContent = "Wiki";
    meta.append(link);
  }
  card.append(meta);
  updateCount();
}

function updateCount() {
  const n = pool().length;
  $("#count").textContent = n
    ? `${n} entries unlocked - about ${Math.round(n / 30.4)} months before one repeats.`
    : "No entries unlocked at this setting.";
}

function buildBookSelect() {
  const sel = $("#book");
  sel.innerHTML = "";
  for (const b of state.dataset.books) {
    const opt = document.createElement("option");
    opt.value = String(b.index);
    opt.textContent = `${b.short} - ${b.title}`;
    if (b.index === state.settings.finishedBook) opt.selected = true;
    sel.append(opt);
  }
  sel.addEventListener("change", () => {
    state.settings.finishedBook = Number(sel.value);
    save();
    render();
  });
}

/* ---------- boot ---------- */

async function boot() {
  try {
    const res = await fetch("entries.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`entries.json returned ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data.entries) || !data.entries.length) {
      throw new Error("entries.json has no entries");
    }
    state.dataset = data;
  } catch (err) {
    state.dataset = window.DCC_FALLBACK || { books: [], entries: [] };
    state.dataset.demo = true;
    state.loadError = err.message;
  }
  if (state.dataset.demo) showDemoNotice();
  if (!state.dataset.books?.length) {
    state.dataset.books = [{ index: 1, title: "Dungeon Crawler Carl", short: "Book 1" }];
  }
  buildBookSelect();
  render();

  // Flip the card at local midnight without needing a reload.
  let shown = dayIndex();
  setInterval(() => {
    const now = dayIndex();
    if (now !== shown) { shown = now; render(); }
  }, 60000);

  $("#reseed").addEventListener("click", () => {
    state.settings.seed = newSeed();
    save();
    render();
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

boot();
