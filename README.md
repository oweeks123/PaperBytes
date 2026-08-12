# PaperBytes

FastAPI service that searches PubMed for recent articles in a curated list of medical journals, summarises each with Claude, and stores results in a SQL database.

## Running locally

No external services required — storage defaults to a local SQLite file.

1. Install dependencies (a virtualenv is recommended):
   ```sh
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. (Optional) Copy `.env.example` to `.env` and fill it in. It is auto-loaded on
   startup. The `/fetch` endpoints need `PUBMED_EMAIL` and `ANTHROPIC_API_KEY`;
   the read endpoints work without any config.
3. Run it:
   ```sh
   python main.py            # http://localhost:8000
   RELOAD=1 python main.py   # with auto-reload for development
   ```
   The `articles` table is created automatically on startup (in `paperbytes.db`).

Then browse the interactive docs at `http://localhost:8000/docs`, or pull in some
real data with `curl -XPOST "localhost:8000/fetch/sync?lookback_days=2"` (requires
the two credentials above).

## Configuration

| Var | Required | Default | Notes |
|---|---|---|---|
| `PUBMED_EMAIL` | for `/fetch` | — | Contact email required by NCBI |
| `ANTHROPIC_API_KEY` | for `/fetch` | — | From console.anthropic.com |
| `DATABASE_URL` | no | `sqlite:///./paperbytes.db` | Point at Postgres for deployment |
| `CLAUDE_MODEL` | no | `claude-haiku-4-5` | Try `claude-sonnet-4-6` for higher quality |
| `LOOKBACK_DAYS` | no | `7` | Fetch window |
| `PORT` | no | `8000` | Listen port |
| `RELOAD` | no | off | Set `1` for uvicorn auto-reload |

Storage is engine-agnostic (SQLAlchemy): SQLite locally, Postgres in a container.
A legacy `postgres://` `DATABASE_URL` is normalised to `postgresql://` automatically.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET` | `/` | Health + config |
| `POST` | `/fetch` | Kick off background fetch of all journals |
| `POST` | `/fetch/sync` | Same, but waits and returns counts (slow; useful for cron) |
| `GET` | `/articles` | List stored articles. Filters: `specialty`, `journal`, `sent`, `limit`, `offset` |
| `GET` | `/articles/{pubmed_id}` | Get one article |
| `PATCH` | `/articles/{pubmed_id}?sent=true` | Mark as sent |
| `DELETE` | `/articles/{pubmed_id}` | Delete |
| `GET` | `/specialties` | Count of articles per specialty |

## Notes

- Default model is `claude-haiku-4-5` since this is high-volume short-summary work — analog of the original `gpt-3.5-turbo`. Set `CLAUDE_MODEL=claude-sonnet-4-6` or `claude-opus-4-7` for higher quality.
- Structured output uses Pydantic (`messages.parse`) instead of `ast.literal_eval` on raw text.
- Articles are keyed by PubMed ID, so re-running `/fetch` skips ones already stored. Specialties live in a related `article_specialties` table so filtering and counts run in portable SQL.
- Deployment will be containerised later; the app already reads `DATABASE_URL` and `PORT` from the environment for that.
