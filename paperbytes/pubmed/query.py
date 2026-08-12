"""PubMed search-term construction from typed inputs.

We compose the query from a :class:`SearchFilters` spec rather than
string-concatenating at call sites, so the retrieval policy is testable and the
exact term is reproducible. The output is returned *unencoded*; URL encoding is
the client's responsibility.

Two design choices worth their weight:

* **``[MHDA]`` (MeSH date) by default, not ``[DP]`` (publication date).** The
  original code filtered on ``[Date - Publication]``, which is unreliable and
  often back-dated. We default to MeSH date because MeSH terms and publication
  types are only assigned when a record is fully indexed; keying the window on
  MeSH date guarantees the ``humans[MeSH]`` / publication-type filters have
  something to match. ``[EDAT]`` (added-to-PubMed date) is available for a
  bleeding-edge window, but it precedes MeSH indexing, so the MeSH-dependent
  filters must be turned off when using it. The date field is selectable per
  request via ``SearchFilters.date_field``.
* **Defensive parenthesisation.** PubMed's implicit operator precedence is a
  footgun (AND/OR/NOT do not bind the way you'd guess). Every group is wrapped in
  its own parentheses so meaning never depends on precedence.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from . import filters
from .models import DateField, JournalScope, SearchFilters

# PubMed search-field tags for each selectable date field.
_DATE_TAGS = {
    DateField.MHDA: "MHDA",
    DateField.EDAT: "EDAT",
    DateField.PDAT: "PDAT",
}


def _quote(term: str) -> str:
    """Quote a term that contains whitespace. Unquoted multi-word phrases are
    interpreted unpredictably by PubMed; single tokens are left bare."""
    return f'"{term}"' if any(ch.isspace() for ch in term) else term


def _or_group(tokens: list[str]) -> str | None:
    """Join tokens with OR inside parentheses. Returns ``None`` for an empty list
    so callers never emit a dangling operator or empty ``()``."""
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0]
    return "(" + " OR ".join(tokens) + ")"


def _resolve_dates(
    spec: SearchFilters, default_lookback_days: int
) -> tuple[date, date]:
    """Resolve the EDAT window. Explicit ``date_from``/``date_to`` win; otherwise
    ``days_back`` (or the caller's default) is measured back from today (UTC)."""
    today = datetime.now(UTC).date()
    date_to = spec.date_to or today
    if spec.date_from is not None:
        return spec.date_from, date_to
    days = spec.days_back if spec.days_back is not None else default_lookback_days
    return date_to - timedelta(days=days), date_to


def _fmt(d: date) -> str:
    return d.strftime("%Y/%m/%d")


def _normalize_journal(title: str) -> str:
    """Normalise a display title into a form PubMed's ``[Journal]`` index matches.

    ``&`` becomes ``and`` and stray ``--`` separators collapse to spaces, which
    recovers the ampersand / en-dash titles (e.g. "Lancet Diabetes & Endocrinology",
    "JAMA Otolaryngology-- Head & Neck Surgery"). Whitespace is collapsed.
    """
    t = title.replace("&", " and ").replace("--", " ")
    return " ".join(t.split())


def journal_clause(title: str) -> str:
    """A single ``[Journal]`` clause for one title.

    NB: the title is left **unquoted** on purpose. A quoted phrase must equal the
    exact NLM title (including a leading "The"), so quoting silently drops most
    display titles; unquoted titles are normalised by PubMed to the right journal.
    """
    return f"{_normalize_journal(title)}[Journal]"


def _journal_group(scope: JournalScope) -> str | None:
    if scope is JournalScope.AIM:
        return filters.JOURNAL_SUBSET_FILTER
    if scope is JournalScope.CURATED:
        # Collapse the curated allowlist into a single OR group — one query
        # instead of the original one-request-per-journal loop.
        return _or_group([journal_clause(j) for j in filters.CURATED_JOURNALS])
    return None  # JournalScope.ALL — no journal restriction


def build_search_term(
    spec: SearchFilters | None = None, *, default_lookback_days: int = 7
) -> str:
    """Compose a PubMed search string from a :class:`SearchFilters` spec.

    With all defaults and a 7-day window ending today this reproduces the
    canonical high-precision clinical query (EDAT window + jsubsetaim + humans +
    English + wanted study designs, excluding comment/editorial/etc.).
    """
    spec = spec or SearchFilters()
    date_from, date_to = _resolve_dates(spec, default_lookback_days)
    tag = _DATE_TAGS[spec.date_field]

    # Positive groups, AND-ed together in order.
    groups: list[str] = [f'("{_fmt(date_from)}"[{tag}] : "{_fmt(date_to)}"[{tag}])']

    journal = _journal_group(spec.journal_scope)
    if journal:
        groups.append(journal)

    if spec.restrict_humans:
        groups.append(filters.SPECIES_FILTER)
    if spec.restrict_english:
        groups.append(filters.LANGUAGE_FILTER)

    if spec.use_included_pub_types:
        # An explicit [] means "no pub-type restriction"; None means "use presets".
        included = (
            spec.included_pub_types
            if spec.included_pub_types is not None
            else list(filters.INCLUDED_PUBLICATION_TYPES)
        )
        group = _or_group(included)
        if group:
            groups.append(group)

    mesh = _or_group([f"{_quote(m)}[MeSH Terms]" for m in spec.mesh_terms])
    if mesh:
        groups.append(mesh)

    if spec.extra_terms and spec.extra_terms.strip():
        groups.append(f"({spec.extra_terms.strip()})")

    term = " AND ".join(groups)

    # Negative group appended as a NOT clause (not AND-ed in).
    if spec.use_excluded_pub_types:
        excluded = (
            spec.excluded_pub_types
            if spec.excluded_pub_types is not None
            else list(filters.EXCLUDED_PUBLICATION_TYPES)
        )
        neg = _or_group(excluded)
        if neg:
            term = f"{term} NOT {neg}"

    return f"({term})"


def describe_term(term: str) -> str:
    """Pretty-print a search term across multiple lines for logging.

    Purely cosmetic: breaks before each top-level ``AND``/``NOT`` so a logged
    query is scannable. Nested OR groups stay on their line.
    """
    return (
        term.replace(" AND ", "\n  AND ")
        .replace(" NOT ", "\n  NOT ")
    )
