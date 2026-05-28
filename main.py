import datetime as dt
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import anthropic
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from pymed import PubMed
from replit import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("paperbytes")

JOURNALS = [
    "Annals of emergency medicine",
    "Internal and emergency medicine",
    "Emergency medicine journal : EMJ",
    "The Journal of Emergency Medicine",
    "Annals of family medicine",
    "The British journal of general practice : the journal of the Royal College of General Practitioners",
    "Journal of the American Board of Family Medicine : JABFM",
    "American family physician",
    "Lancet (London, England)",
    "The New England journal of medicine",
    "Journal of the American Medical Association",
    "Nature medicine",
    "British medical journal",
    "Annals of internal medicine",
    "Annals of surgery",
    "European urology",
    "JAMA surgery",
    "The Journal of urology",
    "British Journal of surgery",
    "Surgery",
    "Laryngoscope",
    "Otolaryngology--head and neck surgery : official journal of American Academy of Otolaryngology-Head and Neck Surgery",
    "The Journal of laryngology and otology",
    "The lancet. Diabetes endocrinology",
    "Nature reviews. Endocrinology",
    "British journal of sports medicine",
]

SUMMARY_TASK = (
    "Summarise the aim of the following journal article abstract by extracting the "
    "salient points. The summary must be 50 words or fewer. Also list the medical "
    "specialties the article is relevant to (e.g. 'Cardiology', 'Emergency Medicine')."
)

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
PUBMED_EMAIL = os.environ["PUBMED_EMAIL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))
ARTICLE_PREFIX = "article:"

pubmed = PubMed(tool="PaperBytes", email=PUBMED_EMAIL)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


class ArticleSummary(BaseModel):
    summary: str = Field(description="50-word-or-fewer summary of the article's aim and key findings")
    specialties: list[str] = Field(description="Medical specialties this article is relevant to")


class Article(BaseModel):
    pubmed_id: str
    title: str
    abstract: str
    ai_summary: str
    ai_specialties: list[str]
    publication_date: str
    journal: str
    pubmed_url: str
    sent: bool = False
    fetched_at: str


def _key(pubmed_id: str) -> str:
    return f"{ARTICLE_PREFIX}{pubmed_id}"


def summarise(abstract: str) -> ArticleSummary:
    response = claude.messages.parse(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SUMMARY_TASK,
        messages=[{"role": "user", "content": f"Abstract:\n{abstract}"}],
        output_format=ArticleSummary,
    )
    if response.parsed_output is None:
        raise ValueError(f"Claude returned no parseable output (stop_reason={response.stop_reason})")
    return response.parsed_output


def fetch_journal(journal: str, since: str, until: str) -> int:
    query = (
        f'(({journal}[Journal]) AND '
        f'(("{since}"[Date - Publication] : "{until}"[Date - Publication]))) '
        f'AND (fha[Filter])'
    )
    saved = 0
    for result in pubmed.query(query, max_results=100):
        pubmed_id = result.pubmed_id[0:8].strip()
        if not pubmed_id:
            continue
        if _key(pubmed_id) in db:
            continue
        if not result.abstract:
            continue

        try:
            summary = summarise(result.abstract)
        except Exception as e:
            log.warning("Claude summarisation failed for %s: %s", pubmed_id, e)
            continue

        article = Article(
            pubmed_id=pubmed_id,
            title=result.title or "",
            abstract=result.abstract,
            ai_summary=summary.summary,
            ai_specialties=summary.specialties,
            publication_date=str(result.publication_date),
            journal=result.journal or journal,
            pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
            sent=False,
            fetched_at=dt.datetime.utcnow().isoformat(),
        )
        db[_key(pubmed_id)] = article.model_dump()
        saved += 1
    return saved


def fetch_all_journals(lookback_days: int) -> dict[str, int]:
    today = dt.datetime.today()
    since = (today - dt.timedelta(days=lookback_days)).strftime("%Y/%m/%d")
    until = today.strftime("%Y/%m/%d")
    results: dict[str, int] = {}
    for journal in JOURNALS:
        try:
            results[journal] = fetch_journal(journal, since, until)
            log.info("Fetched %d new articles from %s", results[journal], journal)
        except Exception as e:
            log.exception("Failed fetching %s: %s", journal, e)
            results[journal] = -1
    return results


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("PaperBytes starting with model=%s lookback=%d days", CLAUDE_MODEL, LOOKBACK_DAYS)
    yield


app = FastAPI(title="PaperBytes", lifespan=lifespan)


@app.get("/")
def health():
    return {"status": "ok", "model": CLAUDE_MODEL, "journals": len(JOURNALS)}


@app.post("/fetch")
async def trigger_fetch(background_tasks: BackgroundTasks, lookback_days: Optional[int] = None):
    days = lookback_days if lookback_days is not None else LOOKBACK_DAYS
    background_tasks.add_task(run_in_threadpool, fetch_all_journals, days)
    return {"status": "started", "lookback_days": days}


@app.post("/fetch/sync")
async def fetch_sync(lookback_days: Optional[int] = None):
    days = lookback_days if lookback_days is not None else LOOKBACK_DAYS
    counts = await run_in_threadpool(fetch_all_journals, days)
    total = sum(c for c in counts.values() if c >= 0)
    return {"status": "complete", "total_saved": total, "by_journal": counts}


@app.get("/articles")
def list_articles(
    specialty: Optional[str] = Query(None, description="Filter by specialty (case-insensitive substring)"),
    journal: Optional[str] = Query(None, description="Filter by journal (case-insensitive substring)"),
    sent: Optional[bool] = Query(None, description="Filter by sent status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    matches: list[dict] = []
    for key in db.prefix(ARTICLE_PREFIX):
        article = dict(db[key])
        if sent is not None and article.get("sent") != sent:
            continue
        if journal and journal.lower() not in article.get("journal", "").lower():
            continue
        if specialty:
            specs = [s.lower() for s in article.get("ai_specialties", [])]
            if not any(specialty.lower() in s for s in specs):
                continue
        matches.append(article)

    matches.sort(key=lambda a: a.get("fetched_at", ""), reverse=True)
    return {
        "total": len(matches),
        "limit": limit,
        "offset": offset,
        "articles": matches[offset : offset + limit],
    }


@app.get("/articles/{pubmed_id}")
def get_article(pubmed_id: str):
    key = _key(pubmed_id)
    if key not in db:
        raise HTTPException(status_code=404, detail="Article not found")
    return dict(db[key])


@app.patch("/articles/{pubmed_id}")
def update_article(pubmed_id: str, sent: bool):
    key = _key(pubmed_id)
    if key not in db:
        raise HTTPException(status_code=404, detail="Article not found")
    article = dict(db[key])
    article["sent"] = sent
    db[key] = article
    return article


@app.delete("/articles/{pubmed_id}")
def delete_article(pubmed_id: str):
    key = _key(pubmed_id)
    if key not in db:
        raise HTTPException(status_code=404, detail="Article not found")
    del db[key]
    return {"status": "deleted", "pubmed_id": pubmed_id}


@app.get("/specialties")
def list_specialties():
    counts: dict[str, int] = {}
    for key in db.prefix(ARTICLE_PREFIX):
        for s in db[key].get("ai_specialties", []):
            counts[s] = counts.get(s, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
