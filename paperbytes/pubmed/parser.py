"""EFetch XML -> :class:`PubMedArticle`.

Parsing is defensive by design: only ``pmid`` and ``title`` are guaranteed by
NCBI, so every other field degrades to a sensible default rather than raising. A
single malformed record is skipped, not allowed to sink the whole page.
"""

from __future__ import annotations

from lxml import etree

from .models import (
    AbstractSection,
    Author,
    MeshTerm,
    PartialDate,
    PubMedArticle,
)

# PubMed abbreviates months as three-letter names; sometimes they are numeric.
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class XmlErrorResponse(Exception):
    """Raised when EFetch returns a 200 response whose body is an NCBI ``<ERROR>``
    document rather than article data."""


def raise_for_xml_error(content: bytes | str) -> None:
    """Detect NCBI's 200-with-error-body failure mode and raise.

    NCBI sometimes returns HTTP 200 with a body like ``<eFetchResult><ERROR>...``
    or a bare ``<ERROR>`` element. Callers run this before trusting a response.
    """
    root = _to_root(content)
    if root is None:
        return
    if root.tag == "ERROR":
        raise XmlErrorResponse((root.text or "").strip() or "NCBI returned <ERROR>")
    err = root.find(".//ERROR")
    if err is not None and root.find(".//PubmedArticle") is None:
        raise XmlErrorResponse((err.text or "").strip() or "NCBI returned <ERROR>")


def _to_root(content: bytes | str) -> etree._Element | None:
    data = content.encode("utf-8") if isinstance(content, str) else content
    if not data.strip():
        return None
    # recover=True so stray entities/markup don't abort the whole parse.
    parser = etree.XMLParser(recover=True, resolve_entities=False)
    return etree.fromstring(data, parser=parser)


def _text(el: etree._Element | None) -> str | None:
    """Full text content of an element including tail text of inline children
    (``<i>``, ``<sup>``, ...). A naive ``el.text`` silently truncates at the first
    inline tag, dropping the rest of the sentence."""
    if el is None:
        return None
    text = "".join(el.itertext()).strip()
    return text or None


def _parse_partial_date(el: etree._Element | None) -> PartialDate | None:
    """Parse a ``<PubDate>``/``<PubMedPubDate>`` element into a PartialDate.

    Handles the structured Year/Month/Day form and the free-text ``<MedlineDate>``
    form (e.g. "2026 Aug-Sep"), never inventing missing precision.
    """
    if el is None:
        return None

    medline = el.findtext("MedlineDate")
    if medline:
        return _parse_medline_date(medline)

    year = el.findtext("Year")
    month_raw = el.findtext("Month")
    day = el.findtext("Day")
    if not year:
        return None

    month: int | None = None
    if month_raw:
        m = month_raw.strip().lower()
        month = _MONTHS.get(m[:3]) if not m.isdigit() else int(m)

    return PartialDate(
        year=int(year),
        month=month,
        day=int(day) if day and day.isdigit() else None,
    )


def _parse_medline_date(text: str) -> PartialDate | None:
    tokens = text.replace("-", " ").split()
    year: int | None = None
    month: int | None = None
    for tok in tokens:
        if tok.isdigit() and len(tok) == 4 and year is None:
            year = int(tok)
        elif tok[:3].lower() in _MONTHS and month is None:
            month = _MONTHS[tok[:3].lower()]
    return PartialDate(year=year, month=month) if year else None


def _parse_doi(article_el: etree._Element, pubmed_data_el: etree._Element | None) -> str | None:
    """DOI lives in ``PubmedData/ArticleIdList`` and *sometimes* only in the
    article's ``ELocationID``. Prefer the former, fall back to the latter."""
    if pubmed_data_el is not None:
        for aid in pubmed_data_el.findall(".//ArticleId"):
            if aid.get("IdType") == "doi" and aid.text:
                return str(aid.text).strip()
    for eloc in article_el.findall("ELocationID"):
        if eloc.get("EIdType") == "doi" and eloc.text:
            return str(eloc.text).strip()
    return None


def _parse_abstract(article_el: etree._Element) -> tuple[str | None, list[AbstractSection]]:
    """Return (flattened_abstract, labelled_sections).

    Structured abstracts carry multiple ``<AbstractText Label="METHODS">``
    elements; we preserve the labels (they materially help downstream extraction)
    and also join them into one flat string for the storage layer.
    """
    sections: list[AbstractSection] = []
    for at in article_el.findall("Abstract/AbstractText"):
        text = _text(at)
        if text is None:
            continue
        sections.append(AbstractSection(label=at.get("Label"), text=text))

    if not sections:
        return None, []

    flat = "\n\n".join(
        f"{s.label}: {s.text}" if s.label else s.text for s in sections
    )
    return flat, sections


def _parse_authors(article_el: etree._Element) -> list[Author]:
    authors: list[Author] = []
    for a in article_el.findall("AuthorList/Author"):
        collective = a.findtext("CollectiveName")
        if collective:
            name = collective.strip()
        else:
            last = (a.findtext("LastName") or "").strip()
            fore = (a.findtext("ForeName") or "").strip()
            name = " ".join(p for p in (fore, last) if p)
        if not name:
            continue
        affiliation = a.findtext("AffiliationInfo/Affiliation")
        authors.append(Author(name=name, affiliation=affiliation.strip() if affiliation else None))
    return authors


def _parse_mesh(citation_el: etree._Element) -> list[MeshTerm]:
    terms: list[MeshTerm] = []
    for mh in citation_el.findall("MeshHeadingList/MeshHeading"):
        desc = mh.find("DescriptorName")
        if desc is None or not desc.text:
            continue
        terms.append(
            MeshTerm(term=desc.text.strip(), major_topic=desc.get("MajorTopicYN") == "Y")
        )
    return terms


def _entrez_date(pubmed_data_el: etree._Element | None) -> PartialDate | None:
    """EDAT — when PubMed added the record to Entrez. Prefer PubStatus="entrez",
    fall back to "pubmed"."""
    if pubmed_data_el is None:
        return None
    history = pubmed_data_el.find("History")
    if history is None:
        return None
    for status in ("entrez", "pubmed"):
        el = history.find(f'PubMedPubDate[@PubStatus="{status}"]')
        if el is not None:
            return _parse_partial_date(el)
    return None


def parse_article(
    pubmed_article_el: etree._Element, *, include_raw: bool = False
) -> PubMedArticle | None:
    """Parse one ``<PubmedArticle>`` element. Returns ``None`` if it lacks the two
    guaranteed fields (pmid, title) — such a record is unusable downstream."""
    citation = pubmed_article_el.find("MedlineCitation")
    if citation is None:
        return None
    article = citation.find("Article")
    if article is None:
        return None

    pmid = citation.findtext("PMID")
    title = _text(article.find("ArticleTitle"))
    if not pmid or not title:
        return None

    pubmed_data = pubmed_article_el.find("PubmedData")
    flat_abstract, sections = _parse_abstract(article)

    return PubMedArticle(
        pmid=pmid.strip(),
        doi=_parse_doi(article, pubmed_data),
        title=title,
        abstract=flat_abstract,
        abstract_sections=sections,
        journal=article.findtext("Journal/Title"),
        journal_iso=article.findtext("Journal/ISOAbbreviation"),
        publication_date=_parse_partial_date(article.find("Journal/JournalIssue/PubDate")),
        entrez_date=_entrez_date(pubmed_data),
        publication_types=[
            pt.text.strip()
            for pt in article.findall("PublicationTypeList/PublicationType")
            if pt.text and pt.text.strip()
        ],
        mesh_terms=_parse_mesh(citation),
        authors=_parse_authors(article),
        keywords=[
            kw.text.strip()
            for kw in citation.findall("KeywordList/Keyword")
            if kw.text and kw.text.strip()
        ],
        language=article.findtext("Language"),
        raw_xml=etree.tostring(pubmed_article_el, encoding="unicode") if include_raw else None,
    )


def parse_efetch_xml(content: bytes | str, *, include_raw: bool = False) -> list[PubMedArticle]:
    """Parse a full ``<PubmedArticleSet>`` EFetch response into articles.

    Malformed individual records are skipped, not fatal. Call
    :func:`raise_for_xml_error` first if you need to distinguish an NCBI error
    body from a legitimately empty result set.
    """
    root = _to_root(content)
    if root is None:
        return []
    articles: list[PubMedArticle] = []
    for el in root.findall(".//PubmedArticle"):
        try:
            parsed = parse_article(el, include_raw=include_raw)
        except Exception:  # noqa: BLE001 — one bad record must not sink the page
            continue
        if parsed is not None:
            articles.append(parsed)
    return articles
