# PaperBytes

FastAPI service that retrieves recent clinical articles from PubMed using hard
filters, summarises each with Claude, and stores results in a SQL database.

Retrieval runs against NCBI E-utilities through an async client
(`paperbytes/pubmed/`): a typed query builder, an `httpx` client with rate
limiting, retries, and history-server paging, and an `lxml` parser that normalises
EFetch XML into typed `PubMedArticle` objects. See
[`PROMPT_layer1_retrieval.md`](PROMPT_layer1_retrieval.md) for the design spec.

## Running locally

No external services required — storage defaults to a local SQLite file.

1. Install dependencies (a virtualenv is recommended):
   ```sh
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. (Optional) Copy `.env.example` to `.env` and fill it in. It is auto-loaded on
   startup. `/search` needs `PUBMED_EMAIL`; `/fetch` additionally needs
   `ANTHROPIC_API_KEY`; the read endpoints (`/articles`, `/specialties`) work
   without any config.
3. Run it:
   ```sh
   python main.py            # http://localhost:8000
   RELOAD=1 python main.py   # with auto-reload for development
   ```
   The tables are created automatically on startup (in `paperbytes.db`).

Then browse the interactive docs at `http://localhost:8000/docs`, or open the
**demo UI at `http://localhost:8000/ui/`** — a plain HTML/CSS/JS page (in `web/`,
no build step). Its **Home (free tier)** tab shows a single random appraised paper
(summary, critical-appraisal table, reported statistics, PubMed link, Download-PDF)
and re-rolls on refresh; the other tabs exercise `/search`, `/articles`, and
`/specialties`.

The `/random` and `/fetch` endpoints call Anthropic to generate the summary +
appraisal (one call per paper, then cached). **Without API credits, set
`MOCK_ANALYSIS=1`** to fill the appraisal from article metadata so the whole UI is
demoable; turn it off once credits are available for real AI analysis.

To preview what retrieval pulls without summarising or storing:

```sh
curl "localhost:8000/search?days_back=3&limit=5"          # AIM core journals
curl "localhost:8000/search?days_back=3&journal_scope=all&limit=5"
```

To fetch, summarise, and store (needs both credentials):

```sh
curl -XPOST "localhost:8000/fetch/sync?lookback_days=2"
```

### Getting an NCBI API key (recommended, not required)

Retrieval works anonymously at NCBI's default 3 requests/second. Registering a
free API key raises that to 10/s:

1. Sign in at <https://www.ncbi.nlm.nih.gov/account/>.
2. Open **Account Settings → API Key Management** and create a key.
3. Put it in `.env` as `NCBI_API_KEY=...` (and set `PUBMED_EMAIL`). The client
   detects the key and switches to the 10/s limit automatically.

## Configuration

| Var | Required | Default | Notes |
|---|---|---|---|
| `PUBMED_EMAIL` | for `/search`, `/fetch` | — | Contact email required by NCBI's usage policy |
| `NCBI_API_KEY` | no | — | Raises the NCBI rate limit from 3/s to 10/s |
| `NCBI_TOOL` | no | `PaperBytes` | Tool name sent to NCBI |
| `PUBMED_PAGE_SIZE` | no | `100` | EFetch page size / history-server paging threshold |
| `PUBMED_TIMEOUT_SECONDS` | no | `20` | Per-request timeout |
| `ANTHROPIC_API_KEY` | for `/fetch` | — | From console.anthropic.com |
| `CLAUDE_MODEL` | no | `claude-haiku-4-5` | Try `claude-sonnet-4-6` for higher quality |
| `LOOKBACK_DAYS` | no | `7` | Default fetch/search window |
| `DATABASE_URL` | no | `sqlite:///./paperbytes.db` | Point at Postgres for deployment |
| `LOG_LEVEL` | no | `INFO` | structlog level |
| `PORT` | no | `8000` | Listen port |
| `RELOAD` | no | off | Set `1` for uvicorn auto-reload |
| `MOCK_ANALYSIS` | no | off | Set `1` to fill `/random` appraisals from metadata instead of calling Anthropic (demo without API credits) |

Storage is engine-agnostic (SQLAlchemy): SQLite locally, Postgres in a container.
A legacy `postgres://` `DATABASE_URL` is normalised to `postgresql://` automatically.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET` | `/` | Health + config (model, NCBI key configured, rate limit, mock flag) |
| `GET` | `/geo` | Resolve the client's country from their IP (localhost → GB). Drives country-gated advertising rules. `?country=XX` overrides for testing |
| `GET` | `/random` | Free-tier home feed: a random article from the past N days (default 30) with an AI summary + critical-appraisal table. Analyses each paper once, then caches |
| `GET` | `/articles/{pubmed_id}/summary.pdf` | Portfolio PDF of a stored article's summary + appraisal |
| `POST` | `/articles/{pubmed_id}/summary.pdf` | Same PDF, with an optional (transient, unstored) practitioner reflection in the body |
| `GET` | `/search` | Live retrieval preview (query params). Does not summarise or store. Returns the resolved NCBI term |
| `POST` | `/search` | Same, taking a full `SearchFilters` body (custom pub-types, MeSH terms, `extra_terms`) |
| `POST` | `/fetch` | Kick off a background fetch+summarise+store pass |
| `POST` | `/fetch/sync` | Same, but waits and returns counts (slow; useful for cron) |
| `GET` | `/articles` | List stored articles. Filters: `specialty`, `journal`, `sent`, `limit`, `offset` |
| `GET` | `/articles/{pubmed_id}` | Get one article |
| `PATCH` | `/articles/{pubmed_id}?sent=true` | Mark as sent |
| `DELETE` | `/articles/{pubmed_id}` | Delete |
| `GET` | `/specialties` | Count of articles per specialty |

### Search filters

`/search` and `/fetch` build a hard-filtered PubMed query. Defaults target recent,
high-quality clinical evidence:

- **Date field (`date_field`)**: `mhda` (MeSH date, **default**), `edat`
  (added-to-PubMed date), or `pdat` (publication date). MeSH terms and publication
  types are only assigned once a record is fully MeSH-indexed, which lags
  publication by weeks. Keying the window on **MeSH date** means the result set is
  MeSH-complete, so the `humans[MeSH]` and publication-type filters actually match
  recent records. Use `edat` for a bleeding-edge window, but then turn the MeSH
  filters off (see below) or you will exclude everything not yet indexed.
- **`journal_scope`**: `curated` (the project's curated allowlist, **default**),
  `all` (no journal restriction), or `aim`. The curated list is loaded from
  **`article_bucket.txt`** at the backend root — one journal title per line — so
  the scope can be edited without touching code. **Note:** `aim` (`jsubsetaim`) is
  retired at NCBI and matches nothing — kept only for backward compatibility.
- **Species / language**: humans + English by default; each toggleable. Because
  the default date field is MHDA, `humans[MeSH]` is safe to leave on.
- **Publication types**: includes RCTs, meta-analyses, systematic reviews, practice
  guidelines, observational studies; excludes comments, editorials, letters,
  retractions, preprints. Both lists are overridable (pass `[]` to disable a group,
  omit to use the presets).
- `extra_terms` (freeform, AND-ed) and `mesh_terms` (OR-ed) for `POST /search`.

Every search/fetch response echoes the exact `resolved_term` sent to NCBI.

> **Tip:** if a query returns nothing, it is almost always the MeSH lag. Either
> keep `date_field=mhda` (recommended — the set stays MeSH-complete), or switch to
> `date_field=edat` with `restrict_humans=false` and the included pub-types off for
> a truly-just-indexed view.

## Development

```sh
pytest            # unit + parser (fixtures) + client (respx) tests; no network
mypy              # strict type-check of the paperbytes/ package
ruff check paperbytes/
```

## Tiers & advertising (in progress)

The UI shows a country flag (top-right, from `/geo`) and a tier switcher. Advertising
is gated by country + tier — **UK rules first**:

- **Free** — random appraised articles, generic Google AdSense slot (placeholder).
- **Free registered practitioner** — (registration is currently simulated by the
  switcher) full pharma / POM advertising in the UK; an optional **reflection** can be
  added to the downloaded PDF but is **not stored** (discarded on refresh).
- **Paid registered practitioner** — pharma / POM advertising, plus a searchable
  **reading list** with a stored, updatable reflection. *(Not yet built — needs real
  accounts; see below.)*

Real registration/login and the paid reading list are the next phase.

## Notes

- Default model is `claude-haiku-4-5` since this is high-volume short-summary work.
  Set `CLAUDE_MODEL=claude-sonnet-4-6` or `claude-opus-4-7` for higher quality.
- Retrieval is fully async (`httpx`); the synchronous Claude summarisation call is
  off-loaded to a threadpool so the event loop is never blocked.
- Articles are keyed by PubMed ID, so re-running `/fetch` skips ones already
  stored. Specialties live in a related `article_specialties` table so filtering
  and counts run in portable SQL.
- Rich parsed fields (DOI, MeSH terms, structured abstract sections, Entrez date)
  are available from retrieval but not all persisted yet — adding columns for them
  is a later migration. The storage mapping lives in `to_storage_fields`.
- Deployment will be containerised later; the app already reads `DATABASE_URL` and
  `PORT` from the environment for that.
