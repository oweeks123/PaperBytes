# CLAUDE.md

Guidance for Claude Code working in this repo. Read this first — it captures intent,
conventions, and non-obvious gotchas that aren't visible from the code alone.

## What this is

**Paper Heroes** (internal name PaperBytes) — a clinical-evidence web app. Each
page load deals ONE recently-published, randomly-chosen medical paper,
AI-summarised + critically appraised, shown as a comic-book **trading card** with
an AI-generated hero/villain illustration of the topic. See `README.md` for the
product/deploy overview; this file is the working context for making changes.

Status: **deployed to production** on Render at **https://paperheroes.io** (Docker
image, managed Postgres, Cloudflare DNS; auto-deploys from `main`). Both the
**free tier** and the **paid "Card Decks" tier** are built and live:
- **Free tier** — the random-card experience above, with a Google AdSense unit.
- **Paid tier** — signed-in practitioners can save cards into named **Card Decks**,
  scroll a deck, open a card, and write a **reflection on the back** (the card
  flips). Upgrade is currently *simulated* (`/auth/upgrade`, no Stripe).
- **Registered (middle) tier** — accounts exist; its distinct frontend feature
  (a *transient* reflection added to the PDF, not stored) is not built yet.

## Architecture at a glance

```
Browser ──/ui──▶ SvelteKit SPA (multi-route: /, /decks, /decks/[id]; served by FastAPI)
                     │ fetch /random, /articles/{pmid}/image, /geo, /contact, PDF,
                     │       /auth/*, /decks/*, /cards/{pmid}/reflection
                     ▼
                 FastAPI (main.py)
                   ├─ paperbytes/pubmed  → NCBI E-utilities (retrieval)
                   ├─ Anthropic Claude   → summary + critical appraisal (cached in DB)
                   ├─ OpenAI gpt-image-1 → illustration (WebP, cached in DB)
                   └─ SQLAlchemy         → SQLite (dev) / Postgres (prod)
```

Everything is one FastAPI service. The frontend is same-origin at `/ui` (no CORS in
prod; Vite proxies to `:8000` in dev). The bare `/` **redirects browsers to `/ui/`**
(content-negotiated) while still serving the health JSON to platform health checks;
`/healthz` always returns that JSON. Because the SPA now has client-side routes,
the `/ui` mount uses `SPAStaticFiles` (serves `index.html` for unknown `/ui/*`
paths so deep links / refreshes on `/ui/decks` resolve; real `_app/*` misses 404).

### The `/random` flow (the core path)

1. Build a hard-filtered PubMed query over the curated journals in
   `article_bucket.txt`, dated on **`[MHDA]`** (MeSH date — NOT publication date, so
   `humans[MeSH]`/pub-type filters actually match), within `days_back`.
2. Pick a random PMID from the result set.
3. **If already analysed** (row in `articles`), return the cached appraisal —
   **no AI spend**. Otherwise call Claude once (`messages.parse` → structured
   `PaperAnalysis`), store, return.
4. Frontend then lazily requests `/articles/{pmid}/image`; the server generates the
   illustration once (gpt-image-1 → WebP), caches in `article_images`, serves it.

**The cache-once rule is load-bearing** — it's how the app stays cheap. Never make a
change that re-analyses or re-generates an image for a PMID that already has one.

## Layout

- `main.py` — the whole API: ORM models, pydantic schemas, AI calls, image gen, all
  routes, StaticFiles mount. Big but deliberately single-file. Includes the tier
  models/endpoints: `User` + auth (`/auth/register|me|upgrade|downgrade`), and the
  Card Decks (`Deck`, `DeckCard`, `CardReflection` tables; `/decks*` +
  `/cards/{pmid}/reflection`, all `require_paid`). The legacy flat `/reading-list`
  endpoints remain but are superseded by decks in the UI.
- `paperbytes/` — typed, side-effect-free support code. **Passes `mypy --strict`
  and is unit-tested.** Keep new pure logic here, not in `main.py`.
  - `config.py` `Settings` (pydantic-settings, case-insensitive env). `get_settings()`
    is cached.
  - `pubmed/` — `query.py` (term building, journal clauses, `[MHDA]` default),
    `client.py` (`PubMedClient`, httpx + tenacity, history server, POST for big
    queries), `parser.py` (lxml), `models.py`, `filters.py` (loads `article_bucket.txt`).
  - `geo.py`, `pdf.py` (reportlab).
- `frontend/` — SvelteKit (Svelte 5 runes).
  - `src/routes/+layout.svelte` — global chrome: top nav + account menu, session
    init, hosts the auth modal.
  - `src/routes/+page.svelte` — home (the deal-a-card page, contact modal,
    paid-only "Add to deck").
  - `src/routes/decks/+page.svelte` — **My Decks** (decks as card piles).
  - `src/routes/decks/[id]/+page.svelte` — deck view (scrollable card strip → open).
  - `src/lib/components/` — `EvidenceCard.svelte` (the card), `ReflectiveCard.svelte`
    (3D flip: front = EvidenceCard, back = reflection), `AuthModal.svelte`,
    `AddToDeckModal.svelte`.
  - `src/lib/session.svelte.ts` (auth/session runes store) and `ui.svelte.ts`
    (shared "open auth modal" state).
  - `src/lib/api.ts` — typed client, `toCard()` + `deckCardToCardModel()`,
    auth-aware fetch (`setAuthToken`) and all auth/deck calls.
- `tests/`, `docs/`, `article_bucket.txt`, `validate_journals.py`.

## Conventions & gotchas

**Environment:**
- Work now happens in **Claude Code on the web** (Linux, bash). Node 20+ and Python
  3.12 are available; `npm run build` and `pytest` run directly. The original dev
  machine was Windows/PowerShell (Node at `C:\Program Files\nodejs\`, prepend to
  PATH) — only relevant if you're back on that box.
- Outbound network is restricted by an egress policy: fonts.googleapis.com,
  onrender.com, and `git push --delete` (branch deletion) are **blocked** from the
  session. GitHub reads/writes go through the GitHub MCP tools, not `gh`.

**Backend:**
- Run with `python main.py` (reads `.env`). No migration framework —
  `Base.metadata.create_all` on startup. New table = free; **new column on an
  existing table needs a manual migration or a dev DB rebuild** (delete
  `paperbytes.db`).
- AI: Anthropic uses `messages.parse` with a pydantic `output_format`
  (`PaperAnalysis` → `ArticleSummary` + `CriticalAppraisal`). **Anthropic has no
  image API** — that's why OpenAI is a second dependency.
- Illustrations: `IMAGE_PROMPT` in `main.py` is a **locked-style** prompt (fixed
  palette, sunburst, waist-up) that only varies hero-vs-villain and the topic —
  this keeps the art consistent. Don't loosen the style clause casually. Images are
  re-encoded PNG→WebP (`_to_webp`, ~26KB) before storage.
- `MOCK_ANALYSIS=1` fills appraisals from metadata (no Anthropic spend) for
  design/demo work.
- **Tiers/auth:** lightweight, passwordless — `/auth/register` (email +
  professional registration) returns a bearer token; `require_user`/`require_paid`
  gate routes. `/auth/upgrade` is a *simulated* upgrade to `paid` (no Stripe).
- **Card Decks:** `Deck` (named collection), `DeckCard` (membership), and
  `CardReflection` — the reflection is stored **once per `(user, article)` and
  shared across all that user's decks** (the "back of the card"), NOT per
  deck-card. These are new tables (created on startup; no migration).
- `main.py` routes/AI are verified by **integration testing** (FastAPI TestClient),
  not committed unit tests — and `main.py` is outside the `ruff`/`mypy` scope
  (those target `paperbytes/`); pre-existing `main.py` lint (e.g. unused `os`) is
  left alone.

**Frontend:**
- Svelte 5 runes (`$state`, `$props`), scoped styles, **no Tailwind**.
- `adapter-static` SPA: `paths.base = '/ui'`, `fallback: 'index.html'`, `ssr=false`.
  Build with `npm run build` → `frontend/build` (gitignored — must build before
  serving). Client routes (`/decks`, `/decks/[id]`) rely on the server's
  `SPAStaticFiles` fallback to resolve on refresh/deep-link.
- Session/auth lives in `session.svelte.ts` (runes singleton, token in
  `localStorage`, `setAuthToken()` wired into `api.ts`). Paid-only UI (My Decks nav,
  Add-to-deck, reflections) is gated on `session.isPaid`.
- The reflection **card flip** is a CSS 3D transform (`transform-style: preserve-3d`,
  `backface-visibility: hidden`, `rotateY(180deg)`). `preserve-3d` makes a stacking
  context, so the flip button bar is lifted with `position: relative; z-index` to
  stay tappable.
- `svelte-check` must stay at **0 errors** (`npm run check`).
- Design = the **"sticker" theme** (see `docs/card-design-mockup.html`): grape
  #7B5BE8, melon #FF5F7E, mint #5BD6A6, butter #FFC94D, sky #9BE8FF, ink #2A2340;
  cream page #FFF4E3; thick ink borders + hard offset shadows; Plus Jakarta Sans +
  JetBrains Mono + Bangers.
- Gotcha: **CSS custom properties don't work in inline SVG presentation attributes**
  (`fill="var(--x)"` fails) — use hex.
- The placeholder while an image generates: CSS sunburst with pulsing "Your hero is
  coming!" text (**only the words pulse**); the generated art uses `object-fit:
  cover` in a 3:2 panel so the **whole hero** shows.

## Hard product constraints (do not regress)

These were explicit user decisions — honour them:
- Title is **"Paper Heroes"** (was "Paper Hero" — corrected). The live domain is
  **`paperheroes.io`** (it moved from the earlier single-r `paperheros.io`). Subline
  reads EXACTLY:
  `ONE PAPER, DRAWN AT RANDOM FROM THE LAST 30 DAYS · APPRAISED BY AI.`
- **No forest plot. No rarity system. No CPD tariff.** (All previously requested,
  then explicitly cut.)
- **Nav** appears for signed-in users; the **My Decks** tab and Add-to-deck are
  **paid-only**. Signed-out users see just a "Sign in" chip (no tabs).
- The card shows the reported statistics (OR/RR/CI/p) **above** the stat block with
  a plain-language significance comment, plus an AI-interpretation **caveat** at the
  bottom of the card.
- Analyse/illustrate **once per PMID, then cache** (the cost model).
- Deck **reflections are shared per card across all of a user's decks** (not
  per-deck) — an explicit product decision.

## SECURITY — read before every commit

- **Developer email `ohweeks@gmail.com` must NEVER appear in the frontend or any
  committed file.** It lives only in `.env` as `CONTACT_EMAIL`, used server-side.
  The `/contact` endpoint never returns it. Verify:
  `grep -rl "ohweeks@gmail.com" frontend/ main.py` must return nothing.
- **API keys** (Anthropic `sk-ant-api03-…`, OpenAI `sk-proj-…`) live ONLY in the
  gitignored `.env`. Never commit, print, or echo them. They were pasted in chat
  during development — advise the user to **rotate** them.
- Pre-commit check (run every time):
  ```sh
  git diff --cached | grep -cE "sk-ant-api03|sk-proj-"      # must be 0
  git diff --cached --name-only | grep -E "\.env$|\.db$|\.png$|\.jpg$"   # must be empty
  ```
- `.gitignore` already excludes `.env`, `*.db`, generated `*.png`/`*.jpg`, caches.
  Don't stage `frontend/build` or `node_modules`.
- The **AdSense publisher ID** (`ca-pub-…` in `app.html` + `/ads.txt`) is *public*
  by design — fine to commit. It is not a secret.

## Working here

- Before editing typed code in `paperbytes/`, remember it must stay
  `mypy --strict` clean and unit-tested. Run `pytest`, `mypy`, `ruff check` before
  committing.
- After frontend changes: `npm run build` **and** `npm run check` (svelte-check, 0
  errors), then confirm the app serves at `/ui/`.
- **Branch/flow:** work lands via PRs into `main`; `main` auto-deploys to Render.
  The active working branch is `claude/webapp-deployment-strategy-yw5342`. If its PR
  is already merged, restart it from the latest `main` for the next change (a
  merged PR can't take new commits). Stale `backend` / `claude/*` branches can only
  be deleted via the GitHub UI (egress policy blocks `git push --delete`).
- Reference docs are in `docs/` (`retrieval-layer-spec.md`,
  `product-tiers-brief.md`, `card-design-mockup.html`).

## Deployment (Render)

- Single Docker image (multi-stage: build SvelteKit → Python runtime), described by
  `render.yaml` (a Render Blueprint: web service + managed Postgres, `DATABASE_URL`
  wired automatically, secrets set in the dashboard). Health check → `/`.
- Live at **https://paperheroes.io** (Cloudflare DNS-only CNAMEs → the Render
  service; TLS auto-issued). `autoDeploy` rebuilds on every push to `main`.
- **`DATABASE_URL` MUST be Postgres in prod.** Accounts, decks, reflections, and the
  appraisal/image cache all live in the DB — on the container's ephemeral SQLite
  they'd be wiped on every redeploy (and the cache would re-bill Anthropic/OpenAI).
- AdSense: loader in `app.html`, `/ads.txt` route, one `<ins>` unit on the home
  card. Nothing renders until Google approves the site.

## Roadmap (where future work goes)

See `docs/product-tiers-brief.md`. **Done:** free tier, paid **Card Decks** tier
(accounts + decks + shared reflections, full frontend), Render deployment, custom
domain, AdSense. **Remaining:**
- **Payments** — replace the simulated `/auth/upgrade` with real **Stripe** checkout
  + webhook.
- **Auth hardening** — currently passwordless (email + registration → token); add
  password or email-link verification.
- **Registered tier** — its one unbuilt frontend feature: a *transient* reflection
  added to the PDF (not stored), for the middle tier.
- **Advertising** — real **pharma/POM** ad units, country-gated via `/geo` (UK rules
  first); today it's a single generic AdSense unit.
- **Infra** — Alembic migrations; SMTP for contact delivery.
