# Claude Code prompt — Layer 1: PubMed hard-filter retrieval (PaperBytes)

Paste everything below the line into Claude Code from the root of the PaperBytes backend
(the directory containing `main.py`).

---

Build the retrieval layer of PaperBytes, an existing FastAPI PubMed literature digest
service. **This is a brownfield task: read `main.py` first.** The app already runs — it
fetches PubMed articles with `pymed`, summarises them with Claude, and stores them in a
SQL database via SQLAlchemy. There is no frontend yet (it was intentionally removed and
will be rebuilt), so every capability must be reachable through the HTTP API and through a
plain function call. Do not build any UI.

You are replacing the current naive, synchronous `pymed`-based retrieval with a robust,
async, hard-filtered NCBI E-utilities client — **without breaking the existing storage,
summarisation, or read endpoints.**

## Ground truth — what already exists (do not reinvent or duplicate)

- Single-file `main.py` FastAPI app. Entry point is `main.py` run directly
  (`python main.py`, honouring `PORT` and `RELOAD` env vars). Keep that entry point.
- **Storage (keep as the system of record):** SQLAlchemy 2.0 models `Article`
  (`pubmed_id` PK, `title`, `abstract`, `ai_summary`, `publication_date` [str],
  `journal`, `pubmed_url`, `sent`, `fetched_at`) and a child `Specialty` table. Storage
  defaults to SQLite (`sqlite:///./paperbytes.db`), Postgres via `DATABASE_URL`
  (Heroku `postgres://` is normalised to `postgresql://`). `Base.metadata.create_all` runs
  on startup.
- **Summarisation (OUT OF SCOPE — do not modify):** `summarise()` calls
  `anthropic` `messages.parse` with `CLAUDE_MODEL` (default `claude-haiku-4-5`) and the
  `ArticleSummary` pydantic model. Leave this untouched.
- **Existing endpoints (keep their paths and behaviour):** `GET /` (health),
  `POST /fetch`, `POST /fetch/sync`, `GET /articles`, `GET /articles/{pubmed_id}`,
  `PATCH /articles/{pubmed_id}`, `DELETE /articles/{pubmed_id}`, `GET /specialties`.
  The scheme is flat and unversioned — stay consistent with it. Do **not** introduce a
  `/api/v1` prefix.
- **Config today** is scattered `os.environ` reads: `PUBMED_EMAIL`, `ANTHROPIC_API_KEY`,
  `CLAUDE_MODEL`, `LOOKBACK_DAYS`, `DATABASE_URL`, `PORT`, `RELOAD`. A local `.env` is
  auto-loaded via `python-dotenv`. Preserve every one of these names.
- **The curated journal list:** `JOURNALS` (~26 titles) is currently iterated one query
  per journal. This is a business rule to preserve as an *option*, not to delete.

## Scope

This task covers **retrieval and parsing only** — fetching a candidate set of articles
from NCBI E-utilities using hard filters, and normalising them into typed objects. Do not
implement summarisation, embedding, relevance scoring, or LLM calls of any kind — those
already exist or belong to later layers. Design the boundary so the existing summarise +
store pipeline consumes your output cleanly.

## Stack (add to the existing `requirements.txt`)

- Keep: FastAPI, `pydantic` v2, SQLAlchemy, `anthropic`, `python-dotenv`, `uvicorn`.
- Add: `httpx` (async), `pydantic-settings`, `lxml`, `tenacity`, and for tests
  `pytest` + `pytest-asyncio` + `respx`. Add `structlog` for structured logging.
- **Remove `pymed`** once the new client replaces it — that is the point of this layer.
- Do **not** use Biopython's `Entrez` module — it is synchronous and hides the request
  semantics I need to control.
- If no lockfile is present you may keep the existing `pip`/`requirements.txt` workflow;
  do not switch the project to a different package manager just for this.

## Layout

Introduce a package next to `main.py`; do not scatter modules at the repo root and do not
create a competing `app/` tree. `main.py` stays the FastAPI entry point and imports from
the package.

```
main.py                       FastAPI app + existing endpoints (rewired, not rewritten)
paperbytes/
  __init__.py
  config.py                   Settings via pydantic-settings (replaces scattered os.environ)
  pubmed/
    __init__.py
    query.py                  Query term construction
    client.py                 Async E-utilities client
    parser.py                 EFetch XML -> PubMedArticle
    models.py                 Pydantic transport models
    filters.py                Filter constants and presets
tests/
  fixtures/                   Saved XML/JSON responses
```

## 1. Query construction (`paperbytes/pubmed/query.py`)

Expose `build_search_term(...) -> str` that composes a PubMed search string from typed
inputs rather than string-concatenating at call sites. It must produce, by default, the
equivalent of:

```
(("2026/08/05"[EDAT] : "2026/08/12"[EDAT])
 AND jsubsetaim[Filter]
 AND humans[MeSH Terms]
 AND English[Language]
 AND (randomizedcontrolledtrial[pt] OR meta-analysis[pt]
      OR systematicreview[pt] OR "practice guideline"[pt]
      OR observationalstudy[pt])
 NOT (comment[pt] OR editorial[pt] OR letter[pt]
      OR retractedpublication[pt] OR preprint[pt]))
```

Requirements:

- Date window uses `[EDAT]` (Entrez date), **not** `[DP]`. The current code uses
  `[Date - Publication]`; that is unreliable and frequently back-dated. EDAT reflects when
  PubMed actually indexed the record, which is what a daily cron job needs. Document this
  reasoning in the docstring. Format dates as `YYYY/MM/DD`.
- Accept either an explicit `date_from`/`date_to` pair or a `days_back: int`, resolving the
  latter against `datetime.now(UTC)`. `days_back` must default to the existing
  `LOOKBACK_DAYS` setting so behaviour stays consistent.
- Every filter group must be independently toggleable and overridable — journal subset,
  species, language, included publication types, excluded publication types. Put the
  defaults in `filters.py` as module-level constants with a short comment explaining each.
  `jsubsetaim` restricts to the Abridged Index Medicus (~120 core clinical journals) and is
  the highest-yield relevance filter, so it defaults on but must be switchable off.
- **Preserve the curated `JOURNALS` list** as a selectable journal-subset filter group:
  when enabled it ORs `"<title>"[Journal]` across the list (this is the app's current
  behaviour, collapsed into one query instead of one-request-per-journal). Default it
  **off** in favour of `jsubsetaim`, but keep it a first-class toggle. Move the list out of
  `main.py` into `filters.py`.
- Support an optional freeform `extra_terms: str` that is AND-ed into the query, and an
  optional `mesh_terms: list[str]` that is OR-ed into its own group.
- Parenthesise every group defensively. PubMed's implicit operator precedence is a footgun.
- Quote any term containing whitespace.
- Return the term unencoded; URL encoding is the client's job.
- Add a `describe_term(term: str) -> str` helper that pretty-prints the query across
  multiple lines for logging.

## 2. E-utilities client (`paperbytes/pubmed/client.py`)

An async `PubMedClient` class holding a shared `httpx.AsyncClient`, constructed with
settings injected — no module-level globals (the current lazy `_pubmed`/`get_pubmed`
singleton pattern is being replaced by DI).

- Base URL `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`.
- Every request must carry `tool` and `email` parameters and the `api_key` when configured.
  Source `tool` from `NCBI_TOOL` (default `PaperBytes`), `email` from the existing
  `PUBMED_EMAIL`, and the key from `NCBI_API_KEY`. NCBI's usage policy requires the first
  two and will block unidentified traffic.
- Rate limiting: enforce a client-side limit of 10 requests/second when an API key is
  present, 3/second when not. Implement it as an `asyncio.Semaphore` plus a token-bucket or
  monotonic-clock spacing — do not rely on `time.sleep`. Make the limit a settings value
  derived from key presence, not a hardcoded literal at the call site.
- `esearch(term, retmax, retstart)` calls `esearch.fcgi` with `db=pubmed`, `retmode=json`,
  `usehistory=y`. Capture and return `WebEnv` and `QueryKey` alongside the count and ID list.
- `efetch(...)` calls `efetch.fcgi` with `db=pubmed`, `retmode=xml`, `rettype=abstract`. It
  must support two modes: fetching by explicit ID list, and fetching from the history server
  via `WebEnv`/`QueryKey` with `retstart`/`retmax`. Use the history-server path when the
  result count exceeds the page size (`PUBMED_PAGE_SIZE`, default 100) — this is the correct
  way to page large sets and avoids enormous URLs.
- When passing an explicit ID list, use POST rather than GET once the list exceeds ~200 IDs.
- Retry on 429 and 5xx with exponential backoff and jitter via `tenacity`, capped at 5
  attempts. Do not retry 4xx other than 429. NCBI returns 200 with an XML `<ERROR>` body in
  some failure cases — detect and raise on that too.
- Provide `search_and_fetch(...)` that composes the above and yields parsed
  `PubMedArticle`s in pages, as an async generator, so callers are not forced to hold the
  whole result set in memory. This is the seam the existing `/fetch` pipeline will consume.
- Raise a small hierarchy of typed exceptions (`PubMedError`, `PubMedRateLimitError`,
  `PubMedResponseError`) rather than letting `httpx` errors escape.

## 3. Models (`paperbytes/pubmed/models.py`)

A `PubMedArticle` pydantic model — **named distinctly from the existing SQLAlchemy
`Article` storage model to avoid a clash.** Fields, at minimum: `pmid`, `doi`, `title`,
`abstract`, `abstract_sections` (ordered label/text pairs), `journal`, `journal_iso`,
`publication_date`, `entrez_date`, `publication_types` (list), `mesh_terms` (list),
`authors` (list of name + affiliation), `keywords`, `language`, `is_open_access` (leave
`None` for now), `raw_xml` (optional, off by default).

Notes for the parser (`parser.py`):

- Only `pmid` and `title` are truly guaranteed. Everything else must be optional with a
  sensible default. A large fraction of records lack abstracts entirely.
- DOI appears in `PubmedData/ArticleIdList/ArticleId[@IdType="doi"]` and *sometimes* only in
  `ELocationID[@EIdType="doi"]`. Check both, preferring the former.
- Abstracts are often structured: multiple `<AbstractText>` elements carrying a `Label`
  attribute (BACKGROUND, METHODS, RESULTS, CONCLUSIONS). Preserve the labels in
  `abstract_sections` and also produce a flattened `abstract` string (the flattened form is
  what today's `Article.abstract` column stores). The labelled structure materially improves
  downstream extraction accuracy, so do not throw it away.
- `<AbstractText>` may contain inline markup (`<i>`, `<sup>`). Extract full text content
  including tail text; a naive `.text` access silently truncates.
- Dates may be partial (year only, or year+month). Model this — do not coerce to a `date` by
  inventing a day. A `PartialDate` value object or a plain string field with a separate
  parsed field is fine; pick one and be consistent. (The storage layer keeps
  `publication_date` as a string today; your model is the richer source.)
- MeSH terms live in `MeshHeadingList/MeshHeading/DescriptorName`; capture the
  `MajorTopicYN` attribute, as later layers will weight major topics differently.

### Mapping to storage (the boundary that keeps the app working)

Provide a pure function `to_storage_article(pubmed_article) -> Article` (returning the
existing SQLAlchemy model) that maps `PubMedArticle` onto the current schema: `pubmed_id`
from `pmid`, flattened `abstract`, `publication_date` as the existing string form,
`journal`, and `pubmed_url` (`https://pubmed.ncbi.nlm.nih.gov/{pmid}/`). Leave
`ai_summary`/`specialties` for the untouched summarisation step to fill. New rich fields
(`doi`, `mesh_terms`, `entrez_date`) do **not** get persisted in this layer — note in a
comment that adding columns for them is a later, separate migration.

## 4. API surface (`main.py`, consistent with the existing flat scheme)

Keep all existing endpoints working. Add retrieval-preview endpoints in the same flat,
unversioned style (no `/api/v1`):

- `GET /search` — query params for `days_back` or `date_from`/`date_to`, plus optional
  overrides for the filter toggles, `limit`, and `offset`. Runs the new client and returns a
  paginated envelope containing `total_count`, `returned`, the parsed articles, and the
  resolved search term used. This does **not** summarise or store — it is a live preview of
  what retrieval would pull.
- `POST /search` — same, but taking a full filter specification as a request body, for
  queries too complex for query params.
- Extend the existing `GET /` health payload to also report whether an NCBI API key is
  configured and the effective rate limit, **without echoing the key**.
- **Rewire `POST /fetch` and `POST /fetch/sync`** to drive the new async client via
  `search_and_fetch(...)` instead of the per-journal `pymed` loop, then run the *existing,
  unchanged* `summarise()` on each article (in a threadpool, since anthropic is sync) and
  persist via `to_storage_article`. Preserve the response shapes and the
  credential-precondition (`400` when `PUBMED_EMAIL`/`ANTHROPIC_API_KEY` are missing).
  Preserve the "skip PMIDs already stored" dedupe.
- Return the resolved search term in every search/fetch response. When I get unexpected
  results I need to see exactly what was sent to NCBI without reading logs.
- Use FastAPI dependency injection for the client and settings so tests can override them.
- Set sensible `response_model`s and let FastAPI generate the OpenAPI schema properly — a
  frontend will be built against this later.

## 5. Config (`paperbytes/config.py`)

`Settings` via `pydantic-settings`, reading from environment and `.env`. **Preserve the
existing variable names** and add the new ones:

- Existing (keep): `PUBMED_EMAIL` (**required — fail fast at startup if unset**, and it is
  the NCBI contact email), `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (default `claude-haiku-4-5`),
  `LOOKBACK_DAYS` (default 7), `DATABASE_URL` (default `sqlite:///./paperbytes.db`, with the
  `postgres://` -> `postgresql://` normalisation preserved), `PORT`, `RELOAD`.
- New: `NCBI_API_KEY` (optional), `NCBI_TOOL` (default `PaperBytes`), `PUBMED_PAGE_SIZE`
  (default 100), `PUBMED_TIMEOUT_SECONDS`, `LOG_LEVEL`.

Route the pubmed layer through `Settings` rather than reading `os.environ` directly. Update
`.env.example` to document the new keys alongside the existing ones. Never log the API key.

## 6. Tests

- Unit tests for `build_search_term` covering: default output matches the canonical string
  above; each toggle removing exactly its own clause; date resolution from `days_back`;
  quoting of multi-word terms; the curated-`JOURNALS` toggle producing a correct OR group;
  empty override lists not producing dangling operators.
- Parser tests against **saved fixture XML** committed under `tests/fixtures/` — include at
  least one record with a structured abstract, one with no abstract, one with a partial
  (year-only) date, one with the DOI only in `ELocationID`, and one with inline markup in
  the abstract. Add one test asserting `to_storage_article` maps onto the existing `Article`
  columns correctly.
- Client tests using `respx` to mock transport. Cover the retry path, the
  200-with-`<ERROR>`-body path, and the switch to POST on large ID lists.
- No test may make a live network call.

## Constraints

- Type-annotate everything you add; the new `paperbytes/` package must pass `mypy --strict`
  and `ruff check`. (The legacy code in `main.py` is not strict-typed — scope strict mode to
  the new package rather than doing a big-bang retype of the whole file.)
- Async throughout the retrieval path. No blocking I/O inside request handlers; the sync
  `summarise()` call stays wrapped in a threadpool at the pipeline boundary.
- Structured logging (`structlog`) — log the resolved term, result count, and elapsed time
  for every search. Respect `LOG_LEVEL`.
- Do not add caching yet, but leave an obvious seam for it in the client.
- Docstrings on public functions explaining *why*, particularly for the EDAT choice, the
  `jsubsetaim` filter, and the history-server paging — I will be handing this to colleagues.
- Do not break any existing endpoint, response shape, or the SQLite/Postgres storage
  behaviour. The read endpoints (`/articles`, `/specialties`) must keep working unchanged.

## Deliverables

Working code that keeps the app runnable with `python main.py`, an updated `requirements.txt`
(with `pymed` removed), an updated `.env.example`, a `README.md` section documenting how to
get an NCBI API key and run the retrieval layer, and a passing test suite. Explain any point
where you deviated from this spec and why — especially any tension between the new hard
filters and the app's existing curated-journal behaviour.

Start by reading `main.py`, then laying out the file structure and the `PubMedArticle` /
storage-mapping models, and confirm the approach with me before implementing the client.
