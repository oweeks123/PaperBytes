# PaperBytes

FastAPI service that searches PubMed for recent articles in a curated list of medical journals, summarises each with Claude, and stores results in Replit DB.

## Setup

1. In Replit, add Secrets:
   - `PUBMED_EMAIL` — your contact email (required by NCBI)
   - `ANTHROPIC_API_KEY` — from console.anthropic.com
   - `CLAUDE_MODEL` (optional, default `claude-haiku-4-5`) — try `claude-sonnet-4-6` for higher quality
   - `LOOKBACK_DAYS` (optional, default `7`)
2. Run the repl. FastAPI listens on `$PORT`.

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

OpenAPI docs at `/docs`.

## Notes

- Default model is `claude-haiku-4-5` since this is high-volume short-summary work — analog of the original `gpt-3.5-turbo`. Set `CLAUDE_MODEL=claude-sonnet-4-6` or `claude-opus-4-7` for higher quality.
- Structured output uses Pydantic (`messages.parse`) instead of `ast.literal_eval` on raw text.
- Articles are keyed by PubMed ID, so re-running `/fetch` skips ones already in the DB.
