# PaperBytes

FastAPI service that searches PubMed for recent articles in a curated list of medical journals, summarises each with Claude, and stores results in Postgres.

## Deploying to Heroku

1. Create the app and add the Postgres add-on:
   ```sh
   heroku create your-app-name
   heroku addons:create heroku-postgresql:essential-0
   ```
   The add-on sets `DATABASE_URL` automatically. Tables are created on startup.
2. Set config vars:
   ```sh
   heroku config:set PUBMED_EMAIL=you@example.com
   heroku config:set ANTHROPIC_API_KEY=sk-ant-...
   heroku config:set CLAUDE_MODEL=claude-haiku-4-5   # optional; try claude-sonnet-4-6 for higher quality
   heroku config:set LOOKBACK_DAYS=7                 # optional
   ```
3. Deploy:
   ```sh
   git push heroku HEAD:main
   ```

The `Procfile` runs `uvicorn` bound to Heroku's `$PORT`. For more throughput, run multiple workers with gunicorn (`web: gunicorn main:app -k uvicorn.workers.UvicornWorker`, add `gunicorn` to `requirements.txt`).

## Running locally

1. Start a local Postgres and create a database (e.g. `createdb paperbytes`).
2. Copy `.env.example` to `.env` and fill it in, then export the vars (or use your preferred loader).
3. `pip install -r requirements.txt`
4. `python main.py` — listens on `$PORT` (default `8000`).

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

OpenAPI docs at `/docs`. Scheduled fetches can be driven by the [Heroku Scheduler](https://devcenter.heroku.com/articles/scheduler) add-on hitting `/fetch/sync`.

## Notes

- Default model is `claude-haiku-4-5` since this is high-volume short-summary work — analog of the original `gpt-3.5-turbo`. Set `CLAUDE_MODEL=claude-sonnet-4-6` or `claude-opus-4-7` for higher quality.
- Structured output uses Pydantic (`messages.parse`) instead of `ast.literal_eval` on raw text.
- Storage is Postgres via SQLAlchemy; the `articles` table is created automatically on startup. Articles are keyed by PubMed ID, so re-running `/fetch` skips ones already stored.
