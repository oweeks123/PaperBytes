import datetime as dt
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import anthropic
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from pymed import PubMed
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

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

# Heroku provisions DATABASE_URL with the legacy "postgres://" scheme, which
# SQLAlchemy no longer accepts — normalise it to "postgresql://".
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/paperbytes")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Separator used to join the specialties array for substring filtering. Chosen
# so it can never appear inside a specialty name or a user's query, which keeps
# a match from spanning two adjacent array elements.
_SPECIALTY_SEP = "\x1f"

pubmed = PubMed(tool="PaperBytes", email=PUBMED_EMAIL)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    pubmed_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    ai_specialties: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    publication_date: Mapped[str] = mapped_column(String, nullable=False, default="")
    journal: Mapped[str] = mapped_column(String, nullable=False, default="")
    pubmed_url: Mapped[str] = mapped_column(String, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict:
        return {
            "pubmed_id": self.pubmed_id,
            "title": self.title,
            "abstract": self.abstract,
            "ai_summary": self.ai_summary,
            "ai_specialties": list(self.ai_specialties or []),
            "publication_date": self.publication_date,
            "journal": self.journal,
            "pubmed_url": self.pubmed_url,
            "sent": self.sent,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }


class ArticleSummary(BaseModel):
    summary: str = Field(description="50-word-or-fewer summary of the article's aim and key findings")
    specialties: list[str] = Field(description="Medical specialties this article is relevant to")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


def fetch_journal(journal: str, since: str, until: str, db: Session) -> int:
    query = (
        f'(({journal}[Journal]) AND '
        f'(("{since}"[Date - Publication] : "{until}"[Date - Publication]))) '
        f'AND (fha[Filter])'
    )
    saved = 0
    for result in pubmed.query(query, max_results=100):
        # pymed returns pubmed_id as a newline-separated string (the article's
        # PMID followed by any reference PMIDs). Take the first line; slicing by
        # character count truncates 9-digit PMIDs into the wrong id.
        raw_id = result.pubmed_id or ""
        pubmed_id = raw_id.splitlines()[0].strip() if raw_id.strip() else ""
        if not pubmed_id:
            continue
        if db.get(Article, pubmed_id) is not None:
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
            fetched_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(article)
        db.commit()
        saved += 1
    return saved


def fetch_all_journals(lookback_days: int) -> dict[str, int]:
    today = dt.datetime.today()
    since = (today - dt.timedelta(days=lookback_days)).strftime("%Y/%m/%d")
    until = today.strftime("%Y/%m/%d")
    results: dict[str, int] = {}
    db = SessionLocal()
    try:
        for journal in JOURNALS:
            try:
                results[journal] = fetch_journal(journal, since, until, db)
                log.info("Fetched %d new articles from %s", results[journal], journal)
            except Exception as e:
                db.rollback()
                log.exception("Failed fetching %s: %s", journal, e)
                results[journal] = -1
    finally:
        db.close()
    return results


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
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
    db: Session = Depends(get_db),
):
    stmt = select(Article)
    if sent is not None:
        stmt = stmt.where(Article.sent == sent)
    if journal:
        stmt = stmt.where(Article.journal.ilike(f"%{journal}%"))
    if specialty:
        joined = func.array_to_string(Article.ai_specialties, _SPECIALTY_SEP)
        stmt = stmt.where(joined.ilike(f"%{specialty}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Article.fetched_at.desc()).limit(limit).offset(offset)
    ).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "articles": [a.to_dict() for a in rows],
    }


@app.get("/articles/{pubmed_id}")
def get_article(pubmed_id: str, db: Session = Depends(get_db)):
    article = db.get(Article, pubmed_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article.to_dict()


@app.patch("/articles/{pubmed_id}")
def update_article(pubmed_id: str, sent: bool, db: Session = Depends(get_db)):
    article = db.get(Article, pubmed_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    article.sent = sent
    db.commit()
    return article.to_dict()


@app.delete("/articles/{pubmed_id}")
def delete_article(pubmed_id: str, db: Session = Depends(get_db)):
    article = db.get(Article, pubmed_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"status": "deleted", "pubmed_id": pubmed_id}


@app.get("/specialties")
def list_specialties(db: Session = Depends(get_db)):
    specialty = func.unnest(Article.ai_specialties).label("specialty")
    stmt = (
        select(specialty, func.count().label("n"))
        .group_by(specialty)
        .order_by(func.count().desc())
    )
    return {row.specialty: row.n for row in db.execute(stmt).all()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
