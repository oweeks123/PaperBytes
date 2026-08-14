# CLAUDE.md

Guidance for Claude Code working in this repo. Read this first — it captures intent,
conventions, and non-obvious gotchas that aren't visible from the code alone.

## What this is

**Paper Hero** (internal name PaperBytes) — a clinical-evidence web app. The
shipped MVP is the **free tier**: each page load deals ONE recently-published,
randomly-chosen medical paper, AI-summarised + critically appraised, shown as a
comic-book **trading card** with an AI-generated hero/villain illustration of the
topic. See `README.md` for the product/deploy overview; this file is the working
context for making changes.

Status: **free tier is done and being packaged for deployment.** Registered and
paid tiers exist as backend endpoints only (frontend not built — see Roadmap).

## Architecture at a glance

```
Browser ──/ui──▶ SvelteKit SPA (built to frontend/build, served by FastAPI)
                     │ fetch /random, /articles/{pmid}/image, /geo, /contact, PDF
                     ▼
                 FastAPI (main.py)
                   ├─ paperbytes/pubmed  → NCBI E-utilities (retrieval)
                   ├─ Anthropic Claude   → summary + critical appraisal (cached in DB)
                   ├─ OpenAI gpt-image-1 → illustration (WebP, cached in DB)
                   └─ SQLAlchemy         → SQLite (dev) / Postgres (prod)
```

Everything is one FastAPI service. The frontend is same-origin at `/ui` (no CORS in
prod; Vite proxies to `:8000` in dev).

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

- `main.py` (~47KB) — the whole API: ORM models, pydantic schemas, AI calls, image
  gen, all routes, StaticFiles mount. Big but deliberately single-file.
- `paperbytes/` — typed, side-effect-free support code. **Passes `mypy --strict`
  and is unit-tested.** Keep new pure logic here, not in `main.py`.
  - `config.py` `Settings` (pydantic-settings, case-insensitive env). `get_settings()`
    is cached.
  - `pubmed/` — `query.py` (term building, journal clauses, `[MHDA]` default),
    `client.py` (`PubMedClient`, httpx + tenacity, history server, POST for big
    queries), `parser.py` (lxml), `models.py`, `filters.py` (loads `article_bucket.txt`).
  - `geo.py`, `pdf.py` (reportlab).
- `frontend/` — SvelteKit (Svelte 5 runes). `src/routes/+page.svelte` (page shell,
  contact modal), `src/lib/components/EvidenceCard.svelte` (the card),
  `src/lib/api.ts` (typed client + `toCard()` view-model mapping).
- `tests/`, `docs/`, `article_bucket.txt`, `validate_journals.py`.

## Conventions & gotchas

**Environment (Windows dev machine):**
- Shell is **PowerShell**; a Bash tool is also available for POSIX. Docker is **not
  installed** (Dockerfile is written but untested here).
- Node is at `C:\Program Files\nodejs\` and **PATH doesn't refresh** — prepend it
  in npm commands: `$env:PATH = "C:\Program Files\nodejs;$env:PATH"; npm run build`.

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

**Frontend:**
- Svelte 5 runes (`$state`, `$props`), scoped styles, **no Tailwind**.
- `adapter-static` SPA: `paths.base = '/ui'`, `fallback: 'index.html'`. Build with
  `npm run build` → `frontend/build` (gitignored — must build before serving).
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
- Title is **"Paper Hero"**. Subline reads EXACTLY:
  `ONE PAPER, DRAWN AT RANDOM FROM THE LAST 30 DAYS · APPRAISED BY AI.`
- **No forest plot. No rarity system. No CPD tariff.** (All previously requested,
  then explicitly cut.)
- Free-tier UI has **no navigation tabs** (Home only). Reading-list/premium nav is
  paid-tier only, and that frontend isn't built yet.
- The card shows the reported statistics (OR/RR/CI/p) **above** the stat block with
  a plain-language significance comment, plus an AI-interpretation **caveat** at the
  bottom of the card.
- Analyse/illustrate **once per PMID, then cache** (the cost model).

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

## Working here

- Before editing typed code in `paperbytes/`, remember it must stay
  `mypy --strict` clean and unit-tested. Run `pytest`, `mypy`, `ruff check` before
  committing.
- After frontend changes, rebuild (`npm run build`) and confirm the app still
  serves at `/ui/`.
- Work happens on the `backend` branch (remote review branch:
  `origin/claude/repo-review-triplq`). Commit/push only when asked.
- Reference docs are in `docs/` (`retrieval-layer-spec.md`,
  `product-tiers-brief.md`, `card-design-mockup.html`).

## Roadmap (where future work goes)

Backend endpoints already exist for these; the SvelteKit frontend is the pending
work. See `docs/product-tiers-brief.md`.
- **Registered tier** — accounts (lightweight token auth, no password yet),
  pharma/POM ads (country-gated via `/geo`, UK rules first), transient reflection
  added to the PDF (not stored).
- **Paid tier** — searchable stored reading list, stored/updatable reflections;
  currently a *simulated* upgrade (no Stripe).
- **Infra** — Alembic migrations; SMTP for contact delivery; auth hardening.
