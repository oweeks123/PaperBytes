"""Hard-filter presets for PubMed query construction.

Each constant below is a filter *group*. ``query.build_search_term`` combines the
enabled groups; every group is independently toggleable so the retrieval policy
can be tuned per request without editing call sites. Defaults encode the
"high-precision recent clinical evidence" policy the daily digest wants.
"""

from __future__ import annotations

from pathlib import Path

# jsubsetaim = Abridged Index Medicus subset. NOTE: NCBI has RETIRED this subset
# tag — it now matches zero records (verified against live E-utilities). It is
# kept only so JournalScope.AIM still builds the historical term; the working
# journal restriction for this project is JournalScope.CURATED (the curated list
# below), which is the default. Do not rely on AIM for real queries.
JOURNAL_SUBSET_FILTER = "jsubsetaim[Filter]"

# Restrict to human studies.
SPECIES_FILTER = "humans[MeSH Terms]"

# Restrict to English-language records.
LANGUAGE_FILTER = "English[Language]"

# Study designs we want, ordered strongest-evidence first. These are the
# publication types PubMed indexes; overridable per request.
INCLUDED_PUBLICATION_TYPES: tuple[str, ...] = (
    "randomizedcontrolledtrial[pt]",
    "meta-analysis[pt]",
    "systematicreview[pt]",
    '"practice guideline"[pt]',
    "observationalstudy[pt]",
)

# Non-primary-research noise to exclude via a NOT group.
EXCLUDED_PUBLICATION_TYPES: tuple[str, ...] = (
    "comment[pt]",
    "editorial[pt]",
    "letter[pt]",
    "retractedpublication[pt]",
    "preprint[pt]",
)

# Curated journal allowlist. The scope is sourced from ``article_bucket.txt`` at
# the backend root — one journal title per line — so it can be edited without
# touching code. Used when JournalScope.CURATED is selected (the default). The
# titles are passed to PubMed's ``[Journal]`` field, which resolves common titles
# and abbreviations; any line that PubMed cannot match simply contributes nothing.
JOURNAL_LIST_FILE = Path(__file__).resolve().parents[2] / "article_bucket.txt"


def load_curated_journals(path: Path = JOURNAL_LIST_FILE) -> tuple[str, ...]:
    """Read the in-scope journal titles from ``article_bucket.txt`` (one per
    line). Blank lines and surrounding whitespace are ignored; duplicates are
    de-duplicated while preserving order. A missing file yields an empty tuple
    (the app still boots; a CURATED search then applies no journal restriction)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    deduped: dict[str, None] = {}
    for line in lines:
        name = line.strip()
        if name:
            deduped.setdefault(name, None)
    return tuple(deduped)


CURATED_JOURNALS: tuple[str, ...] = load_curated_journals()
