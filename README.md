# Paper Hero (PaperBytes)

A daily clinical-evidence "card". Each visit deals **one recently-published paper**,
drawn at random from a curated set of medical journals, **appraised by AI**, and
presented as a comic-book **trading card** — AI summary, critical appraisal, the
reported statistics with a significance read, and an AI-generated **hero/villain
illustration** of the topic (a superhero for beneficial findings, a villain for
harms/risks).

This repository is the **free-tier MVP**, packaged for deployment. The registered
and paid tiers exist as backend endpoints and are on the roadmap for the frontend.

---

## Stack

- **Backend** — FastAPI (Python 3.12), SQLAlchemy (SQLite locally / Postgres in
  production), served with uvicorn.
- **Frontend** — SvelteKit (Svelte 5, `adapter-static`, scoped component styles),
  built to static files and served by FastAPI at **`/ui`** (same origin, no CORS).
- **Retrieval** — PubMed via NCBI E-utilities (`paperbytes/pubmed`).
- **AI** — **Anthropic Claude** for the summary + critical appraisal;
  **OpenAI `gpt-image-1`** for the card illustration. (Anthropic has no image API,
  hence the second provider.)

## Project structure

```
pb-backend/
├─ main.py                 FastAPI app: routes, ORM models, AI calls, image gen
├─ paperbytes/             support package (passes mypy --strict)
│  ├─ config.py            Settings via pydantic-settings
│  ├─ geo.py               IP → country (country-gated ads)
│  ├─ pdf.py               summary/appraisal PDF (reportlab)
│  └─ pubmed/              E-utilities client, query builder, XML parser, models, filters
├─ frontend/               SvelteKit app → builds to frontend/build, served at /ui
│  └─ src/lib/components/  EvidenceCard.svelte (the trading card), …
├─ tests/                  pytest (query / parser / client / geo / pdf / filters)
├─ docs/                   design mockup + specs (see below)
├─ article_bucket.txt      curated journal allowlist (one title per line)
├─ validate_journals.py    checks the bucket resolves against PubMed
├─ Dockerfile / .dockerignore
├─ requirements.txt        runtime deps   (requirements-dev.txt = + test/lint)
├─ pyproject.toml          pytest / mypy / ruff config
└─ .env.example
```

## Quick start (development)

Two processes: the API (uvicorn) and the frontend dev server (Vite, which proxies
API calls to the API). Requires **Python 3.12+** and **Node 20+**.

```sh
# 1) Backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # fill in PUBMED_EMAIL + ANTHROPIC_API_KEY (OPENAI_API_KEY optional)
python main.py              # API on http://localhost:8000

# 2) Frontend (separate terminal)
cd frontend
npm install
npm run dev                 # http://localhost:5173/ui  (API proxied to :8000)
```

No credentials? Set `MOCK_ANALYSIS=1` to fill appraisals from metadata; without an
`OPENAI_API_KEY` the card shows the "Your hero is coming!" placeholder. The **read**
endpoints work with no config at all.

## Production build & run

The frontend is built to static files and served by FastAPI, so a deployment is a
single service.

**Docker (recommended):**

```sh
docker build -t paper-hero .
docker run -p 8000:8000 --env-file .env paper-hero
# open http://localhost:8000/ui/
```

**Manual:**

```sh
cd frontend && npm ci && npm run build && cd ..
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

- The app UI is at **`/ui/`**; `/` is a health/config JSON (handy for platform
  health checks).
- `frontend/build` is gitignored — **build it before serving** (the Docker image
  does this in a Node build stage).
- Config is provided at runtime via env vars, never baked into the image.
- For persistence across redeploys, point `DATABASE_URL` at Postgres (SQLite in a
  container is ephemeral, so cached appraisals/illustrations would regenerate).

## Configuration

All via environment / `.env` (see `.env.example`).

| Var | Required | Default | Notes |
|---|---|---|---|
| `PUBMED_EMAIL` | for `/random`,`/search` | — | NCBI contact email |
| `ANTHROPIC_API_KEY` | for appraisal | — | Claude summary + appraisal |
| `CLAUDE_MODEL` | no | `claude-haiku-4-5` | e.g. `claude-sonnet-4-6` for higher quality |
| `MOCK_ANALYSIS` | no | `0` | `1` = metadata mock (no Anthropic spend) |
| `OPENAI_API_KEY` | no | — | Enables card illustrations (gpt-image-1) |
| `IMAGE_QUALITY` | no | `medium` | `low` / `medium` / `high` |
| `CONTACT_EMAIL` | no | — | Contact-form destination (server-side only) |
| `SMTP_HOST/PORT/USER/PASSWORD` | no | —/587 | Deliver contact messages (else stored in DB) |
| `NCBI_API_KEY` | no | — | Raises NCBI rate limit 3→10/s |
| `DATABASE_URL` | no | `sqlite:///./paperbytes.db` | Postgres for deployment |
| `LOOKBACK_DAYS` | no | `7` | Default search window |
| `LOG_LEVEL` / `PORT` / `RELOAD` | no | `INFO`/`8000`/off | |

**Cost note:** each *new* paper triggers one Claude call (cheap) and, if enabled,
one gpt-image-1 image (~$0.01–0.04, `IMAGE_QUALITY`-dependent). Both are cached per
PMID, so repeats are free.

## API

**Free tier (public):**

| Method | Path | What it does |
|---|---|---|
| `GET` | `/` | Health + config |
| `GET` | `/random?days_back=30` | Deal a random appraised paper (summary + appraisal + stats). Analyses once, caches |
| `GET` | `/articles/{pmid}/image` | AI illustration; generated + cached on first request (WebP). 404 without an OpenAI key |
| `GET`/`POST` | `/articles/{pmid}/summary.pdf` | Portfolio PDF (POST body may carry a transient reflection) |
| `POST` | `/contact` | Store + optionally email a contact message (honeypot-protected) |
| `GET` | `/geo` | Client country from IP (drives country-gated ads; UK rules first) |

**Dev / admin:** `GET/POST /search`, `POST /fetch`, `POST /fetch/sync`,
`GET /articles`, `GET/PATCH/DELETE /articles/{pmid}`, `GET /specialties`.

**Registered / paid (backend implemented, frontend pending):**
`POST /auth/register`, `GET /auth/me`, `POST /auth/upgrade|downgrade`,
`POST/GET /reading-list`, `PATCH/DELETE /reading-list/{pmid}`.

Interactive docs at `/docs`.

## How the card is built

- **Retrieval** — a hard-filtered PubMed query over the curated journals
  (`article_bucket.txt`), keyed on **`[MHDA]` (MeSH date)** so records are
  MeSH-complete and the `humans[MeSH]` / publication-type filters actually match.
  See `docs/retrieval-layer-spec.md`.
- **Appraisal** — one Claude `messages.parse` call returns a structured
  `CriticalAppraisal` (PICO, every reported outcome with its stats, a significance
  comment, risk of bias, level of evidence, limitations) plus a conversational
  summary. Cached in the `articles` table.
- **Illustration** — one gpt-image-1 call renders a consistent comic-book
  character (hero for benefits, villain for harms) embodying the topic; re-encoded
  to WebP and cached in `article_images`.

### Journal scope

`article_bucket.txt` is the curated allowlist (one title per line); edit it to
change the scope — no code change. Titles go to PubMed's `[Journal]` field
**unquoted and normalised** (a quoted title must equal the exact NLM name). Verify
the whole list resolves:

```sh
PUBMED_EMAIL=you@example.com python validate_journals.py
```

## Testing & quality

```sh
pytest                          # unit tests: query, parser (fixtures), client (respx), geo, pdf
mypy                            # strict type-check of the paperbytes/ package
ruff check paperbytes/ tests/
```

`main.py` (routes, AI calls) is verified by integration/manual testing rather than
unit tests; the typed, side-effect-free logic lives in `paperbytes/` and is unit
tested + `mypy --strict`.

## Data & migrations

SQLAlchemy models; tables are created on startup via `Base.metadata.create_all`
(**no migration framework**). Adding tables is transparent; **adding columns to an
existing table needs a manual migration** (or a dev DB rebuild). Consider adding
Alembic before the next schema change.

## Roadmap / future development

- **Port the registered + paid tiers to SvelteKit** — the backend endpoints
  (accounts, reading list, stored reflections, tier gating) already exist; the
  earlier vanilla prototype UI for them is in git history (removed here to keep the
  MVP clean). See `docs/product-tiers-brief.md`.
- **Contact delivery** — add SMTP creds (Gmail app password) or swap to a
  transactional email service.
- **Country-gated advertising** — `/geo` + ad policy are wired; add real ad units
  (AdSense free tier; pharma/POM for registered tiers, UK rules first).
- **Auth hardening + payments** — current auth is a lightweight token (no
  password/verification); the paid tier is a simulated upgrade (no Stripe yet).
- **Migrations** — introduce Alembic; persist richer article fields (DOI, MeSH,
  entrez date) currently dropped at the storage boundary.

## Reference docs (`docs/`)

- `docs/retrieval-layer-spec.md` — the PubMed retrieval layer spec.
- `docs/product-tiers-brief.md` — the free/registered/paid tier brief.
- `docs/card-design-mockup.html` — the static "sticker" card design mockup.

## Notes

- Rotate any API keys that were shared during development.
- Default Claude model is `claude-haiku-4-5` (cheap, good for high-volume short
  summaries); switch via `CLAUDE_MODEL`.
