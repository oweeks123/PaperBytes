import datetime as dt
import logging
import os
import random
import secrets
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

# Load a local .env file if present (development convenience; optional dependency).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import anthropic
import httpx
import structlog
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    or_,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from paperbytes import geo
from paperbytes.config import Settings, get_settings
from paperbytes.pdf import build_summary_pdf
from paperbytes.pubmed import filters
from paperbytes.pubmed.client import PubMedClient, PubMedError
from paperbytes.pubmed.models import (
    DateField,
    JournalScope,
    PubMedArticle,
    SearchFilters,
    SearchResponse,
    to_storage_fields,
)
from paperbytes.pubmed.query import build_search_term

settings = get_settings()

# Structured logging (JSON), honouring LOG_LEVEL. structlog routes through stdlib
# logging so uvicorn's handlers still apply.
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(message)s",
)
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
)
log = structlog.get_logger("paperbytes")

SUMMARY_TASK = (
    "Summarise the following journal article abstract in a relaxed, conversational tone — "
    "as if you were explaining it to a colleague over coffee — capturing the aim and the key "
    "findings. Write up to 200 words, but use only as many as the paper genuinely warrants; do "
    "not pad. Also list the medical specialties the article is relevant to (e.g. 'Cardiology', "
    "'Emergency Medicine')."
)

# Anthropic client is created lazily so the app can boot (and serve read-only
# endpoints) without summarisation credentials configured.
_claude: Optional[anthropic.Anthropic] = None


def get_claude() -> anthropic.Anthropic:
    global _claude
    if _claude is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _claude


# Local development defaults to a SQLite file (zero setup). Point DATABASE_URL at
# Postgres for containerised/production deployment; Heroku-style postgres:// URLs
# are normalised to the postgresql:// scheme SQLAlchemy expects.
DATABASE_URL = settings.normalised_database_url
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Specialty(Base):
    __tablename__ = "article_specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    pubmed_id: Mapped[str] = mapped_column(
        ForeignKey("articles.pubmed_id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, index=True)

    article: Mapped["Article"] = relationship(back_populates="specialties")


class Article(Base):
    __tablename__ = "articles"

    pubmed_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[str] = mapped_column(String, nullable=False, default="")
    journal: Mapped[str] = mapped_column(String, nullable=False, default="")
    pubmed_url: Mapped[str] = mapped_column(String, nullable=False)
    doi: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Author display names, stored so cached /random responses are complete.
    authors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Cached CriticalAppraisal dict. Non-null means this paper has been analysed,
    # so it is served without re-billing Anthropic.
    appraisal: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # True if the stored appraisal is a metadata-derived mock (MOCK_ANALYSIS mode),
    # not a real Anthropic result — so it can be replaced once credits are added.
    analysis_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    specialties: Mapped[list["Specialty"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "pubmed_id": self.pubmed_id,
            "title": self.title,
            "abstract": self.abstract,
            "ai_summary": self.ai_summary,
            "ai_specialties": [s.name for s in self.specialties],
            "publication_date": self.publication_date,
            "journal": self.journal,
            "pubmed_url": self.pubmed_url,
            "doi": self.doi,
            "authors": self.authors or [],
            "appraisal": self.appraisal,
            "sent": self.sent,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    professional_registration: Mapped[str] = mapped_column(String, nullable=False)
    # free_registered (default on sign-up) | paid (simulated upgrade)
    tier: Mapped[str] = mapped_column(String, nullable=False, default="free_registered")
    # Opaque session token; the client stores it and sends it as a bearer token.
    # Lightweight (no password) by design — to be hardened later.
    token: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReadingListItem(Base):
    __tablename__ = "reading_list"
    __table_args__ = (UniqueConstraint("user_email", "pubmed_id", name="uq_user_article"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str] = mapped_column(
        ForeignKey("users.email", ondelete="CASCADE"), index=True
    )
    pubmed_id: Mapped[str] = mapped_column(
        ForeignKey("articles.pubmed_id", ondelete="CASCADE"), index=True
    )
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArticleSummary(BaseModel):
    summary: str = Field(description="Conversational summary of up to 200 words (concise, not padded) of the article's aim and key findings")
    specialties: list[str] = Field(description="Medical specialties this article is relevant to")


class Outcome(BaseModel):
    name: str = Field(description="The outcome that was measured")
    measure: Optional[str] = Field(default=None, description="Effect measure, e.g. HR, RR, OR, mean difference")
    value: Optional[str] = Field(default=None, description="Point estimate, e.g. 0.82")
    confidence_interval: Optional[str] = Field(default=None, description="95% confidence interval, e.g. 0.70-0.96")
    p_value: Optional[str] = Field(default=None, description="p-value if reported")


class CriticalAppraisal(BaseModel):
    study_design: str = Field(description="e.g. randomised controlled trial, cohort, meta-analysis")
    population: str = Field(description="Population/setting and sample size")
    intervention: str = Field(description="Intervention or exposure studied")
    comparator: str = Field(description="Comparator or control")
    outcomes: list[Outcome] = Field(description="Every reported outcome with its statistics")
    significance_comment: str = Field(
        default="",
        description="One or two sentences on the statistical significance of the key findings — which reached significance (95% CI excluding the null, or p<0.05) and which did not",
    )
    risk_of_bias: str = Field(description="Risk of bias / methodological quality")
    level_of_evidence: str = Field(description="Level of evidence, e.g. Oxford CEBM 1b")
    limitations: str = Field(description="Key limitations")


class PaperAnalysis(BaseModel):
    summary: str = Field(description="Conversational summary of up to 200 words (concise, not padded) of the article's aim and key findings")
    specialties: list[str] = Field(description="Medical specialties this article is relevant to")
    appraisal: CriticalAppraisal


class RandomArticleResponse(BaseModel):
    pmid: str
    title: str
    journal: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    pubmed_url: str
    abstract: Optional[str] = None
    summary: str
    specialties: list[str]
    appraisal: CriticalAppraisal
    cached: bool = Field(description="True if served from the cache (no Anthropic call was made)")
    mock: bool = Field(default=False, description="True if the appraisal is a metadata-derived mock (no AI credits)")


APPRAISAL_TASK = (
    "You are a clinical evidence appraiser. From the journal article abstract, produce: "
    "(1) a summary of up to 200 words of the aim and key findings, written in a relaxed, "
    "conversational tone — as if explaining the paper to a colleague over coffee. Keep it "
    "clear and engaging rather than stiff and academic, but use only as many words as the "
    "paper genuinely warrants; do not pad for the sake of length. "
    "(2) the medical specialties it is relevant to; and "
    "(3) a structured critical appraisal — study design, population (with sample size), "
    "intervention, comparator, every reported outcome with its statistics (effect measure, "
    "point estimate, 95% CI, p-value), a brief comment on the statistical significance of the "
    "key findings (state which reached significance — CI excluding the null or p<0.05 — and "
    "which did not), risk of bias, level of evidence, and key limitations. "
    "The critical appraisal fields stay precise and clinical — the conversational tone is only "
    "for the summary. Extract statistics verbatim where reported; leave a field blank if the "
    "abstract does not state it. Do not invent numbers."
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pubmed_client(cfg: Settings = Depends(get_settings)) -> PubMedClient:
    """FastAPI dependency yielding a PubMedClient bound to request settings.

    Tests override this (or ``get_settings``) to inject a mocked transport.
    """
    return PubMedClient(cfg)


# --- Auth (lightweight, token-based; no password by design) ----------------
class RegisterRequest(BaseModel):
    email: str
    professional_registration: str = Field(description="e.g. GMC/GDC/NMC registration number")


class UserResponse(BaseModel):
    email: str
    professional_registration: str
    tier: str
    token: str


class ReadingListAdd(BaseModel):
    pubmed_id: str
    reflection: Optional[str] = None


class ReflectionUpdate(BaseModel):
    reflection: Optional[str] = None


class ReadingListItemResponse(BaseModel):
    pubmed_id: str
    title: str
    journal: Optional[str] = None
    pubmed_url: str
    summary: str
    specialties: list[str]
    appraisal: Optional[CriticalAppraisal] = None
    reflection: Optional[str] = None
    added_at: Optional[str] = None
    updated_at: Optional[str] = None


def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Optional[User]:
    """Resolve the caller from a ``Authorization: Bearer <token>`` header, or None."""
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    return db.scalar(select(User).where(User.token == token))


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def require_paid(user: User = Depends(require_user)) -> User:
    if user.tier != "paid":
        raise HTTPException(status_code=403, detail="Paid tier required")
    return user


def _user_response(u: User) -> UserResponse:
    return UserResponse(
        email=u.email, professional_registration=u.professional_registration, tier=u.tier, token=u.token
    )


def _reading_item_response(item: ReadingListItem, art: Article) -> ReadingListItemResponse:
    return ReadingListItemResponse(
        pubmed_id=art.pubmed_id,
        title=art.title,
        journal=art.journal or None,
        pubmed_url=art.pubmed_url,
        summary=art.ai_summary,
        specialties=[s.name for s in art.specialties],
        appraisal=CriticalAppraisal(**art.appraisal) if art.appraisal else None,
        reflection=item.reflection,
        added_at=item.added_at.isoformat() if item.added_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


def summarise(abstract: str) -> ArticleSummary:
    """Summarise an abstract with Claude. Synchronous (the anthropic SDK call is
    blocking); callers on the async path wrap this in ``run_in_threadpool``. This
    is the summarisation layer and is intentionally left unchanged by the
    retrieval work."""
    response = get_claude().messages.parse(
        model=settings.claude_model,
        max_tokens=2048,
        system=SUMMARY_TASK,
        messages=[{"role": "user", "content": f"Abstract:\n{abstract}"}],
        output_format=ArticleSummary,
    )
    if response.parsed_output is None:
        raise ValueError(f"Claude returned no parseable output (stop_reason={response.stop_reason})")
    return response.parsed_output


def analyse(abstract: str) -> PaperAnalysis:
    """Summarise + critically appraise an abstract in one Claude call. Synchronous
    (blocking SDK call); async callers wrap it in ``run_in_threadpool``. Used by the
    on-demand /random path, where each paper is analysed at most once and cached."""
    response = get_claude().messages.parse(
        model=settings.claude_model,
        max_tokens=4096,
        system=APPRAISAL_TASK,
        messages=[{"role": "user", "content": f"Abstract:\n{abstract}"}],
        output_format=PaperAnalysis,
    )
    if response.parsed_output is None:
        raise ValueError(f"Claude returned no parseable output (stop_reason={response.stop_reason})")
    return response.parsed_output


def build_mock_analysis(art: PubMedArticle) -> PaperAnalysis:
    """A metadata-derived placeholder appraisal used when MOCK_ANALYSIS is on (no
    Anthropic credits). Real fields (study design from publication types, a summary
    snippet, specialties from major MeSH) are populated where possible; the rest is
    clearly marked MOCK so the UI/PDF layout can be exercised without pretending to
    be a real appraisal."""
    note = "MOCK — enable Anthropic credits for a real AI appraisal."
    design = ", ".join(art.publication_types) or "Not specified"
    specialties = [m.term for m in art.mesh_terms if m.major_topic][:3] or ["General medicine"]
    # Show the full abstract as the mock summary (the real AI summary is a short
    # 50-word précis; here we don't truncate so the whole text is visible).
    summary = (art.abstract or "").strip() or note
    return PaperAnalysis(
        summary=summary,
        specialties=specialties,
        appraisal=CriticalAppraisal(
            study_design=design,
            population=note,
            intervention=note,
            comparator=note,
            outcomes=[
                Outcome(name="MOCK outcome", measure="RR", value="0.00", confidence_interval="0.00–0.00", p_value="—")
            ],
            risk_of_bias=note,
            level_of_evidence="—",
            limitations=note,
        ),
    )


def _random_response(a: "Article", *, cached: bool) -> RandomArticleResponse:
    """Build the /random payload from a stored (analysed) Article row."""
    return RandomArticleResponse(
        pmid=a.pubmed_id,
        title=a.title,
        journal=a.journal or None,
        authors=list(a.authors or []),
        publication_date=a.publication_date or None,
        doi=a.doi,
        pubmed_url=a.pubmed_url,
        abstract=a.abstract,
        summary=a.ai_summary,
        specialties=[s.name for s in a.specialties],
        appraisal=CriticalAppraisal(**(a.appraisal or {})),
        cached=cached,
        mock=a.analysis_mock,
    )


async def run_fetch(spec: SearchFilters) -> dict:
    """Stream hard-filtered articles from PubMed, summarise each with Claude, and
    persist. Retrieval is async (httpx); the sync ``summarise`` call is off-loaded
    to a threadpool at the boundary so the event loop is never blocked. Records
    already stored (by PMID) or lacking an abstract are skipped."""
    client = PubMedClient(settings)
    seen = 0
    saved = 0
    try:
        async for art in client.search_and_fetch(spec):
            seen += 1
            with SessionLocal() as db:
                if db.get(Article, art.pmid) is not None:
                    continue
                if not art.abstract:
                    continue
                try:
                    summary = await run_in_threadpool(summarise, art.abstract)
                except Exception as e:  # noqa: BLE001 — skip a single bad summary
                    log.warning("summarise_failed", pmid=art.pmid, error=str(e))
                    continue

                article = Article(
                    **to_storage_fields(art),
                    ai_summary=summary.summary,
                    sent=False,
                    fetched_at=dt.datetime.now(dt.timezone.utc),
                    specialties=[Specialty(name=s) for s in dict.fromkeys(summary.specialties)],
                )
                db.add(article)
                db.commit()
                saved += 1
        log.info("fetch_complete", seen=seen, saved=saved)
    finally:
        await client.aclose()
    return {"seen": seen, "saved": saved}


def _require_pubmed_email() -> None:
    if not settings.pubmed_email:
        raise HTTPException(status_code=400, detail="Missing required config: PUBMED_EMAIL")


def _require_fetch_credentials() -> None:
    missing = [
        name
        for name, value in (
            ("PUBMED_EMAIL", settings.pubmed_email),
            ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        )
        if not value
    ]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required config: {', '.join(missing)}")


def _build_filters(
    days_back: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
    date_field: DateField,
    journal_scope: JournalScope,
    restrict_humans: bool,
    restrict_english: bool,
) -> SearchFilters:
    return SearchFilters(
        days_back=days_back,
        date_from=date_from,
        date_to=date_to,
        date_field=date_field,
        journal_scope=journal_scope,
        restrict_humans=restrict_humans,
        restrict_english=restrict_english,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    log.info(
        "startup",
        model=settings.claude_model,
        lookback_days=settings.lookback_days,
        db=engine.url.get_backend_name(),
        ncbi_rate_limit=settings.ncbi_rate_limit,
    )
    yield


app = FastAPI(title="PaperBytes", lifespan=lifespan)

# SvelteKit frontend, built (adapter-static, base /ui) to frontend/build and served
# same-origin so it can call the API without CORS. Browse it at /ui/. Run
# `npm --prefix frontend run build` to (re)generate it; skipped if absent.
_WEB_DIR = Path(__file__).parent / "frontend" / "build"
if _WEB_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=_WEB_DIR, html=True), name="ui")


@app.get("/")
def health():
    return {
        "status": "ok",
        "model": settings.claude_model,
        "journals": len(filters.CURATED_JOURNALS),
        "ncbi_api_key_configured": bool(settings.ncbi_api_key),
        "ncbi_rate_limit": settings.ncbi_rate_limit,
        "mock_analysis": settings.mock_analysis,
    }


@app.get("/geo")
async def geo_lookup(
    request: Request,
    country: Optional[str] = Query(None, description="Override the detected country (ISO-2), for testing"),
):
    """Resolve the client's country from their IP (localhost falls back to GB).
    The country drives the advertising structure — UK rules first. Pass
    ``?country=US`` etc. to preview other countries locally."""
    xff = request.headers.get("x-forwarded-for")
    ip = geo.client_ip(xff, request.client.host if request.client else None)
    if country:
        cc = country.strip().upper()
        name = cc
    else:
        async with httpx.AsyncClient(timeout=5.0) as client:
            cc, name = await geo.lookup_country(ip, client=client)
    return {
        "ip": ip,
        "country_code": cc,
        "country_name": name,
        "flag": geo.flag_emoji(cc),
        "ad_policy": geo.ad_policy(cc),
    }


@app.get("/search", response_model=SearchResponse)
async def search_preview(
    days_back: int = Query(settings.lookback_days, ge=0, description="Search the previous N days. Defaults to LOOKBACK_DAYS (7)."),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    date_field: DateField = Query(DateField.MHDA, description="Date field for the window. MHDA (MeSH date) keeps results MeSH-complete; use EDAT for a bleeding-edge window with the MeSH filters off."),
    journal_scope: JournalScope = JournalScope.CURATED,
    restrict_humans: bool = True,
    restrict_english: bool = True,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    client: PubMedClient = Depends(get_pubmed_client),
):
    """Live preview of PubMed retrieval: runs the hard-filtered query and returns
    parsed articles. Does not summarise or store. The resolved term is always
    returned so you can see exactly what was sent to NCBI."""
    _require_pubmed_email()
    spec = _build_filters(
        days_back, date_from, date_to, date_field, journal_scope, restrict_humans, restrict_english
    )
    try:
        term, result = await client.search(spec)
        if result.count == 0 or offset >= result.count:
            articles = []
        else:
            articles = await client.fetch_page(result, offset=offset, size=limit)
    except PubMedError as e:
        raise HTTPException(status_code=502, detail=f"PubMed retrieval failed: {e}")
    finally:
        await client.aclose()
    return SearchResponse(
        resolved_term=term,
        total_count=result.count,
        returned=len(articles),
        limit=limit,
        offset=offset,
        articles=articles,
    )


@app.post("/search", response_model=SearchResponse)
async def search_preview_post(
    spec: SearchFilters,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    client: PubMedClient = Depends(get_pubmed_client),
):
    """Same as ``GET /search`` but takes a full ``SearchFilters`` body, for
    queries too complex for query params (custom pub-type lists, MeSH terms,
    freeform ``extra_terms``)."""
    _require_pubmed_email()
    try:
        term, result = await client.search(spec)
        if result.count == 0 or offset >= result.count:
            articles = []
        else:
            articles = await client.fetch_page(result, offset=offset, size=limit)
    except PubMedError as e:
        raise HTTPException(status_code=502, detail=f"PubMed retrieval failed: {e}")
    finally:
        await client.aclose()
    return SearchResponse(
        resolved_term=term,
        total_count=result.count,
        returned=len(articles),
        limit=limit,
        offset=offset,
        articles=articles,
    )


@app.post("/fetch")
async def trigger_fetch(background_tasks: BackgroundTasks, lookback_days: Optional[int] = None):
    """Kick off a background fetch+summarise+store pass. Returns immediately with
    the resolved search term so you can confirm what will be queried."""
    _require_fetch_credentials()
    spec = SearchFilters(days_back=lookback_days)
    from paperbytes.pubmed.query import build_search_term

    term = build_search_term(spec, default_lookback_days=settings.lookback_days)
    background_tasks.add_task(run_fetch, spec)
    return {
        "status": "started",
        "lookback_days": lookback_days if lookback_days is not None else settings.lookback_days,
        "resolved_term": term,
    }


@app.post("/fetch/sync")
async def fetch_sync(lookback_days: Optional[int] = None):
    """Fetch+summarise+store synchronously and return counts. Slow; useful for
    cron.

    Response-shape note: the old per-journal ``by_journal`` map is gone — the new
    retrieval is a single hard-filtered query rather than one request per journal
    — replaced by ``seen``/``saved`` and the resolved term. No frontend consumes
    this yet, so the change is safe to make now."""
    _require_fetch_credentials()
    spec = SearchFilters(days_back=lookback_days)
    from paperbytes.pubmed.query import build_search_term

    term = build_search_term(spec, default_lookback_days=settings.lookback_days)
    result = await run_fetch(spec)
    return {
        "status": "complete",
        "total_saved": result["saved"],
        "seen": result["seen"],
        "resolved_term": term,
    }


@app.get("/random", response_model=RandomArticleResponse)
async def random_article(
    days_back: int = Query(30, ge=1, le=365, description="Draw from the past N days."),
    client: PubMedClient = Depends(get_pubmed_client),
    db: Session = Depends(get_db),
):
    """Free-tier home feed. Pick a random article from the past ``days_back`` days
    (curated journals). If it has already been analysed, serve the cached summary +
    appraisal (no Anthropic call); otherwise fetch it, run one Claude call, store,
    and serve. Each paper is therefore analysed at most once."""
    _require_fetch_credentials()
    spec = SearchFilters(days_back=days_back, journal_scope=JournalScope.CURATED)
    term = build_search_term(spec, default_lookback_days=settings.lookback_days)
    try:
        head = await client.esearch(term, retmax=0)
        if head.count == 0:
            raise HTTPException(status_code=404, detail=f"No articles found in the past {days_back} days")
        # Draw one random PMID via a 1-record page at a random offset — avoids
        # pulling the whole id list.
        offset = random.randrange(head.count)
        page = await client.esearch(term, retmax=1, retstart=offset)
        if not page.idlist:
            raise HTTPException(status_code=404, detail="No article at the drawn offset; try again")
        pmid = page.idlist[0]

        # Cache hit only if a *real* appraisal exists (or we're in mock mode, where a
        # stored mock is fine to reuse). A stored mock is a miss in real mode, so it
        # gets replaced by real AI once credits are added.
        existing = db.get(Article, pmid)
        if existing is not None and existing.appraisal and (
            settings.mock_analysis or not existing.analysis_mock
        ):
            log.info("random_cache_hit", pmid=pmid, mock=existing.analysis_mock)
            return _random_response(existing, cached=True)

        fetched = await client.efetch(ids=[pmid])
        if not fetched:
            raise HTTPException(status_code=404, detail=f"Could not fetch article {pmid}")
        art = fetched[0]
        if not art.abstract:
            raise HTTPException(status_code=422, detail=f"Article {pmid} has no abstract to appraise")
    except PubMedError as e:
        raise HTTPException(status_code=502, detail=f"PubMed retrieval failed: {e}")
    finally:
        await client.aclose()

    if settings.mock_analysis:
        analysis = build_mock_analysis(art)
    else:
        analysis = await run_in_threadpool(analyse, art.abstract)

    article = existing or Article(pubmed_id=pmid, fetched_at=dt.datetime.now(dt.timezone.utc))
    for key, value in to_storage_fields(art).items():
        setattr(article, key, value)
    article.ai_summary = analysis.summary
    article.appraisal = analysis.appraisal.model_dump()
    article.analysis_mock = settings.mock_analysis
    article.doi = art.doi
    article.authors = [au.name for au in art.authors]
    article.sent = article.sent if existing is not None else False
    article.specialties = [Specialty(name=s) for s in dict.fromkeys(analysis.specialties)]
    if existing is None:
        db.add(article)
    db.commit()
    log.info("random_analysed", pmid=pmid, mock=settings.mock_analysis)
    return _random_response(article, cached=False)


class PdfReflection(BaseModel):
    reflection: Optional[str] = Field(default=None, description="Optional practitioner reflection to include in the PDF (not stored)")


def _article_pdf_response(pubmed_id: str, reflection: Optional[str], db: Session) -> Response:
    a = db.get(Article, pubmed_id)
    if a is None or not a.appraisal:
        raise HTTPException(
            status_code=404,
            detail="No stored appraisal for this article — open it via /random first.",
        )
    data = a.to_dict() | {
        "pmid": a.pubmed_id,
        "summary": a.ai_summary,
        "specialties": [s.name for s in a.specialties],
        "reflection": reflection,
    }
    return Response(
        content=build_summary_pdf(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="paperbytes-{pubmed_id}.pdf"'},
    )


@app.get("/articles/{pubmed_id}/summary.pdf")
def article_pdf(pubmed_id: str, db: Session = Depends(get_db)):
    """Download a portfolio PDF of the summary + critical appraisal for a stored,
    already-analysed article."""
    return _article_pdf_response(pubmed_id, None, db)


@app.post("/articles/{pubmed_id}/summary.pdf")
def article_pdf_with_reflection(pubmed_id: str, body: PdfReflection, db: Session = Depends(get_db)):
    """Same PDF, but with a practitioner reflection included. The reflection is
    transient — passed at download time and never stored (free registered tier)."""
    return _article_pdf_response(pubmed_id, body.reflection, db)


@app.post("/auth/register", response_model=UserResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register (or, idempotently, sign back in) with an email + professional
    registration. Returns a session token. Lightweight and password-free by
    design — to be hardened later."""
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="A valid email is required")
    reg = body.professional_registration.strip()
    if not reg:
        raise HTTPException(status_code=400, detail="A professional registration is required")
    user = db.get(User, email)
    if user is None:
        user = User(
            email=email,
            professional_registration=reg,
            tier="free_registered",
            token=secrets.token_urlsafe(32),
            created_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(user)
    else:
        user.professional_registration = reg  # returning user: refresh + return token
    db.commit()
    return _user_response(user)


@app.get("/auth/me", response_model=UserResponse)
def auth_me(user: User = Depends(require_user)):
    return _user_response(user)


@app.post("/auth/upgrade", response_model=UserResponse)
def upgrade(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Simulated upgrade to the paid tier (no real payment yet)."""
    user.tier = "paid"
    db.commit()
    return _user_response(user)


@app.post("/auth/downgrade", response_model=UserResponse)
def downgrade(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Revert to the free registered tier (demo convenience)."""
    user.tier = "free_registered"
    db.commit()
    return _user_response(user)


@app.post("/reading-list", response_model=ReadingListItemResponse)
def add_to_reading_list(
    body: ReadingListAdd, user: User = Depends(require_paid), db: Session = Depends(get_db)
):
    """Add the current article to the paid user's reading list, with an optional
    stored reflection (updatable later)."""
    art = db.get(Article, body.pubmed_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Article not found — open it first")
    now = dt.datetime.now(dt.timezone.utc)
    item = db.scalar(
        select(ReadingListItem).where(
            ReadingListItem.user_email == user.email, ReadingListItem.pubmed_id == body.pubmed_id
        )
    )
    if item is None:
        item = ReadingListItem(
            user_email=user.email,
            pubmed_id=body.pubmed_id,
            reflection=body.reflection,
            added_at=now,
            updated_at=now,
        )
        db.add(item)
    else:
        if body.reflection is not None:
            item.reflection = body.reflection
        item.updated_at = now
    db.commit()
    return _reading_item_response(item, art)


@app.get("/reading-list", response_model=list[ReadingListItemResponse])
def get_reading_list(
    q: Optional[str] = Query(None, description="Search title, journal, specialty or reflection"),
    user: User = Depends(require_paid),
    db: Session = Depends(get_db),
):
    stmt = (
        select(ReadingListItem, Article)
        .join(Article, Article.pubmed_id == ReadingListItem.pubmed_id)
        .where(ReadingListItem.user_email == user.email)
    )
    if q:
        like = f"%{q.strip()}%"
        spec_match = select(Specialty.pubmed_id).where(Specialty.name.ilike(like))
        stmt = stmt.where(
            or_(
                Article.title.ilike(like),
                Article.journal.ilike(like),
                ReadingListItem.reflection.ilike(like),
                Article.pubmed_id.in_(spec_match),
            )
        )
    stmt = stmt.order_by(ReadingListItem.updated_at.desc())
    return [_reading_item_response(item, art) for item, art in db.execute(stmt).all()]


@app.patch("/reading-list/{pubmed_id}", response_model=ReadingListItemResponse)
def update_reading_list_reflection(
    pubmed_id: str,
    body: ReflectionUpdate,
    user: User = Depends(require_paid),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(ReadingListItem).where(
            ReadingListItem.user_email == user.email, ReadingListItem.pubmed_id == pubmed_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Not in your reading list")
    item.reflection = body.reflection
    item.updated_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    art = db.get(Article, pubmed_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _reading_item_response(item, art)


@app.delete("/reading-list/{pubmed_id}")
def remove_from_reading_list(
    pubmed_id: str, user: User = Depends(require_paid), db: Session = Depends(get_db)
):
    item = db.scalar(
        select(ReadingListItem).where(
            ReadingListItem.user_email == user.email, ReadingListItem.pubmed_id == pubmed_id
        )
    )
    if item is not None:
        db.delete(item)
        db.commit()
    return {"status": "removed", "pubmed_id": pubmed_id}


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
        matching = select(Specialty.pubmed_id).where(Specialty.name.ilike(f"%{specialty}%"))
        stmt = stmt.where(Article.pubmed_id.in_(matching))

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
    stmt = (
        select(Specialty.name, func.count().label("n"))
        .group_by(Specialty.name)
        .order_by(func.count().desc())
    )
    return {name: n for name, n in db.execute(stmt).all()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.reload,
    )
