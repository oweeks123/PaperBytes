"""Typed transport models for the retrieval layer.

``PubMedArticle`` is the parsed, normalised representation of one EFetch record.
It is named distinctly from the SQLAlchemy ``Article`` storage model in
``main.py`` to avoid a clash: this is the *source* object, that is the *system of
record*. ``SearchFilters`` is the typed input to query construction and doubles
as the request body for ``POST /search``.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class JournalScope(StrEnum):
    """Which journal-restriction filter group to apply."""

    CURATED = "curated"  # the curated journal allowlist (default; see filters.py)
    ALL = "all"          # no journal restriction
    AIM = "aim"          # jsubsetaim[Filter] — RETIRED by NCBI, matches nothing


class DateField(StrEnum):
    """PubMed date field the search window is applied to.

    MHDA is the default because MeSH terms and publication types are only assigned
    once a record is fully MeSH-indexed; selecting by MeSH date guarantees those
    filters have something to match. EDAT (added-to-PubMed date) is earlier but
    precedes MeSH indexing; PDAT is the publisher's publication date.
    """

    MHDA = "mhda"  # MeSH date — when MeSH terms were assigned (default)
    EDAT = "edat"  # Entrez date — when the record was added to PubMed
    PDAT = "pdat"  # Publication date


class Author(BaseModel):
    name: str
    affiliation: str | None = None


class AbstractSection(BaseModel):
    """One labelled block of a structured abstract (e.g. label="METHODS")."""

    label: str | None = None
    text: str


class MeshTerm(BaseModel):
    term: str
    # MajorTopicYN on the DescriptorName; later layers weight major topics higher.
    major_topic: bool = False


class PartialDate(BaseModel):
    """A possibly-incomplete date.

    PubMed dates are frequently year-only or year+month. We model the missing
    precision explicitly rather than coercing to a ``datetime.date`` by inventing
    a day, which would silently fabricate data.
    """

    year: int | None = None
    month: int | None = None
    day: int | None = None

    @property
    def is_empty(self) -> bool:
        return self.year is None and self.month is None and self.day is None

    def __str__(self) -> str:
        # Render as YYYY, YYYY/MM, or YYYY/MM/DD depending on available precision.
        if self.year is None:
            return ""
        parts = [f"{self.year:04d}"]
        if self.month is not None:
            parts.append(f"{self.month:02d}")
            if self.day is not None:
                parts.append(f"{self.day:02d}")
        return "/".join(parts)


class PubMedArticle(BaseModel):
    """A single normalised PubMed record. Only ``pmid`` and ``title`` are
    guaranteed by NCBI; everything else is optional with a sensible default."""

    pmid: str
    doi: str | None = None
    title: str
    abstract: str | None = None
    abstract_sections: list[AbstractSection] = Field(default_factory=list)
    journal: str | None = None
    journal_iso: str | None = None
    publication_date: PartialDate | None = None
    entrez_date: PartialDate | None = None
    publication_types: list[str] = Field(default_factory=list)
    mesh_terms: list[MeshTerm] = Field(default_factory=list)
    authors: list[Author] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    language: str | None = None
    is_open_access: bool | None = None
    # Raw EFetch XML for this record; off by default to keep payloads small.
    raw_xml: str | None = None

    @property
    def pubmed_url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


class SearchFilters(BaseModel):
    """Typed specification of a retrieval query. Passed to
    ``query.build_search_term`` and used as the ``POST /search`` request body.

    Every filter group is independently toggleable. ``included_pub_types`` /
    ``excluded_pub_types`` default to the presets in ``filters.py`` when left
    ``None`` and can be fully overridden.
    """

    # Date window. Provide an explicit range, or days_back (resolved against
    # now(UTC)); if neither is set the caller's default lookback is used.
    days_back: int | None = Field(default=None, ge=0)
    date_from: date | None = None
    date_to: date | None = None

    # Date field the window is applied to. MHDA (MeSH date) by default so the
    # result set is MeSH-complete and the filters below actually match. Switch to
    # EDAT for a bleeding-edge window (but then turn the MeSH filters off, or you
    # will exclude the not-yet-indexed records). See DateField.
    date_field: DateField = DateField.MHDA

    journal_scope: JournalScope = JournalScope.CURATED
    # MeSH-dependent filters. These are ON by default and work because the default
    # date_field is MHDA (records are MeSH-complete). If you switch date_field to
    # EDAT, turn these off.
    restrict_humans: bool = True
    restrict_english: bool = True

    use_included_pub_types: bool = True
    use_excluded_pub_types: bool = True
    included_pub_types: list[str] | None = None
    excluded_pub_types: list[str] | None = None

    # Freeform PubMed syntax AND-ed into the query.
    extra_terms: str | None = None
    # MeSH descriptors OR-ed into their own group.
    mesh_terms: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Envelope for the ``/search`` preview endpoints. Always includes the exact
    resolved term sent to NCBI, so unexpected results can be diagnosed without
    reading logs."""

    resolved_term: str
    total_count: int
    returned: int
    limit: int
    offset: int
    articles: list[PubMedArticle]


def to_storage_fields(article: PubMedArticle) -> dict[str, str]:
    """Map a parsed ``PubMedArticle`` onto the columns of the existing SQLAlchemy
    ``Article`` model, returned as a plain dict.

    Deviation from the spec, deliberately flagged: the spec asks for
    ``to_storage_article(...) -> Article``. Returning the ORM object here would
    force this package to import the model from ``main.py``, while ``main.py``
    imports this package — a circular import. Returning a storage-agnostic dict
    keeps the retrieval layer decoupled from the ORM; ``main.py`` constructs
    ``Article(**to_storage_fields(a), ...)`` at the boundary and attaches the
    AI summary/specialties afterwards. Rich fields (doi, mesh_terms, entrez_date)
    are intentionally not persisted here — adding columns for them is a later,
    separate migration.
    """
    return {
        "pubmed_id": article.pmid,
        "title": article.title or "",
        "abstract": article.abstract or "",
        "publication_date": str(article.publication_date) if article.publication_date else "",
        "journal": article.journal or "",
        "pubmed_url": article.pubmed_url,
    }
