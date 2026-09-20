# Deploying the web version

The site is static: four small files plus `entries.json`. Any host that serves
files over HTTPS will do. HTTPS is not optional — service workers, offline
caching and push all refuse to run without it.

## Test it locally first

```bash
python3 tools/build_dataset.py     # writes data/entries.json and mirrors it into web/
cd web && python3 -m http.server 8000
```

Open `http://localhost:8000`. Service workers are allowed on `localhost`
without TLS, so offline mode works here too.

---

## Read this before you pick a host

`entries.json` is mostly Matt Dinniman's prose (see `NOTICE.md`). Publishing it
at a public URL is *publishing it* — the same thing that rules out the app
stores. A GitHub Pages site is world-readable even when the repo is private.

So the hosting question isn't only "what's easiest", it's "who can reach it".

| | Public URL | Effort | Custom domain | Cost |
|---|---|---|---|---|
| **GitHub Pages** | Yes, always | Lowest | Yes | Free |
| **Cloudflare Pages + Access** | **No — email allowlist** | Low | Yes | Free |
| **Your own server** | Your choice | Medium | Yes | You have one already |
| Netlify / Vercel | Yes (auth is paid) | Low | Yes | Free |

**Recommendation: Cloudflare Pages with Access in front of it.** It's the only
free option that gives you a real front door. You allowlist your own email,
Cloudflare emails you a one-time code the first time each device connects, and
nobody else can load the page at all. That turns "I published an author's prose
on the open web" into "I put my notes behind a login", which is a different
thing entirely.

---

## Option A — Cloudflare Pages + Access (recommended)

1. Push the repo to `bar371/dcc-daily`.
2. Cloudflare dashboard → Workers & Pages → Create → Pages → connect the repo.
   - Build command: *(leave empty)*
   - Build output directory: `web`
3. Commit `data/entries.json` **and** `web/entries.json` so the build has data.
   Both are gitignored by default — remove those two lines from `.gitignore`
   once you've decided you're comfortable with where it's hosted.
4. Zero Trust → Access → Applications → Add a self-hosted app pointing at the
   Pages domain. Policy: *Allow* → *Emails* → your address.

Deploys on every push. Add family emails to the policy if you want them in.

## Option B — GitHub Pages

Simplest, already wired: `.github/workflows/pages.yml` runs the picker tests,
assembles `web/` plus `data/entries.json`, and deploys on every push to `main`.

Enable it once: **Settings → Pages → Source: GitHub Actions**. Lands at
`https://bar371.github.io/dcc-daily/`.

The workflow only ships `entries.json` if that file is committed. Left out, the
site runs on the placeholder data and is harmless to have public — which is a
reasonable way to use this: public shell, real data only on a private host.

## Option C — your own server

You're already running hosting for lasergameoperation.nl. If it's nginx:

```bash
python3 tools/build_dataset.py
rsync -av --delete web/ you@server:/var/www/dcc-daily/
```

```nginx
server {
    listen 443 ssl http2;
    server_name dcc.example.nl;
    root /var/www/dcc-daily;

    # The service worker must never be served stale, or clients pin an old shell.
    location = /sw.js        { add_header Cache-Control "no-cache"; }
    location = /entries.json { add_header Cache-Control "no-cache"; }
    location ~* \.(css|js|svg|png)$ { expires 7d; }

    # auth_basic "DCC"; auth_basic_user_file /etc/nginx/.htpasswd;
}
```

Uncomment the two `auth_basic` lines and you have the private-front-door
property without Cloudflare.

---

## Installing it on a phone

**iOS** (16.4+, and yes this works in the EU — Apple reversed the 17.4 removal
in March 2024): open in **Safari**, Share → Add to Home Screen. Chrome on iOS
can't do it; the button only exists in Safari.

**Android**: Chrome shows an install prompt, or menu → Add to Home screen.

Once installed it runs full-screen, keeps its own storage, and works with the
plane on.

---

## Notifications: the honest position

There is no web API that schedules a local notification for tomorrow morning.
Notification Triggers was a Chrome experiment and never shipped. Every daily
web notification you have ever received was **pushed from a server at that
moment**. So:

**A. No notifications.** Tap the icon when you feel like it. Zero
infrastructure, zero battery, nothing to break. For a fun personal app this is
a perfectly respectable answer and it's where I'd start.

**B. A scheduled shortcut — no server.** The neat middle option.
On iOS: Shortcuts → Automation → Time of Day → 08:00 → Open App → your
installed web app. It opens rather than notifies, but it puts the thing in
front of you daily, which is the actual goal. Android has the same via a
routine or a home-screen widget.

**C. Real push.** Needs a VAPID key pair, a place to store subscriptions, and
a cron. A Cloudflare Worker with a Cron Trigger plus KV does all three on the
free tier — roughly 100 lines. Works on Android immediately, and on iOS only
once the app is on the home screen. Worth doing if B annoys you; not worth
doing first.

Weigh this against the Flutter route, which gets genuinely local scheduled
notifications with no server at all. That is the one real advantage the native
app still has here. Everything else — install, offline, cross-platform, cost —
the web version does better.
