from datetime import date

from paperbytes.pubmed.models import DateField, JournalScope, SearchFilters
from paperbytes.pubmed.query import build_search_term, describe_term

FIXED = {"date_from": date(2026, 8, 5), "date_to": date(2026, 8, 12)}

# The spec's canonical high-precision string. NB: reproducing it requires explicit
# flags — the EDAT date field, the (now-retired) AIM subset, and humans[MeSH] +
# included pub-types. The operational defaults use MHDA + curated journals.
CANONICAL = (
    '(("2026/08/05"[EDAT] : "2026/08/12"[EDAT]) '
    "AND jsubsetaim[Filter] "
    "AND humans[MeSH Terms] "
    "AND English[Language] "
    "AND (randomizedcontrolledtrial[pt] OR meta-analysis[pt] OR systematicreview[pt] "
    'OR "practice guideline"[pt] OR observationalstudy[pt]) '
    "NOT (comment[pt] OR editorial[pt] OR letter[pt] OR retractedpublication[pt] OR preprint[pt]))"
)

# The explicit flags needed to reproduce the spec's canonical string.
CANONICAL_SPEC = {
    "date_field": DateField.EDAT,
    "journal_scope": JournalScope.AIM,
    "restrict_humans": True,
    "use_included_pub_types": True,
}


def test_aim_full_filter_string_matches_spec():
    assert build_search_term(SearchFilters(**FIXED, **CANONICAL_SPEC)) == CANONICAL


def test_default_is_mesh_filtered_curated():
    # Operational default: MHDA date field + curated journals + humans[MeSH] +
    # English + included/excluded pub-types, and NOT the retired AIM tag.
    term = build_search_term(SearchFilters(**FIXED))
    assert "[MHDA]" in term  # MeSH-date window keeps the set MeSH-complete
    # Journal titles are UNQUOTED so PubMed normalises them to the right journal.
    assert "New England Journal of Medicine[Journal]" in term  # curated group
    assert "humans[MeSH Terms]" in term
    assert "English[Language]" in term
    assert "randomizedcontrolledtrial[pt]" in term
    assert " NOT (comment[pt]" in term
    assert "jsubsetaim" not in term


def test_default_date_field_is_mhda_not_dp():
    term = build_search_term(SearchFilters(**FIXED))
    assert "[MHDA]" in term
    assert "[EDAT]" not in term
    assert "[DP]" not in term and "Date - Publication" not in term


def test_date_field_selectable():
    edat = build_search_term(SearchFilters(**FIXED, date_field=DateField.EDAT))
    pdat = build_search_term(SearchFilters(**FIXED, date_field=DateField.PDAT))
    assert '"2026/08/05"[EDAT] : "2026/08/12"[EDAT]' in edat
    assert '"2026/08/05"[PDAT] : "2026/08/12"[PDAT]' in pdat


def test_days_back_resolves_window():
    # date_to fixed so the resolved from-date is deterministic (field-agnostic).
    term = build_search_term(SearchFilters(date_to=date(2026, 8, 12), days_back=5))
    assert '"2026/08/07"[MHDA] : "2026/08/12"[MHDA]' in term


def test_days_back_falls_back_to_default():
    term = build_search_term(SearchFilters(date_to=date(2026, 8, 12)), default_lookback_days=3)
    assert '"2026/08/09"[MHDA]' in term


def test_journal_scope_all_removes_jsubsetaim():
    term = build_search_term(SearchFilters(**FIXED, journal_scope=JournalScope.ALL))
    assert "jsubsetaim" not in term


def test_journal_scope_curated_builds_or_group():
    term = build_search_term(SearchFilters(**FIXED, journal_scope=JournalScope.CURATED))
    assert "New England Journal of Medicine[Journal]" in term
    assert "[Journal] OR " in term
    assert "jsubsetaim" not in term


def test_journal_clause_normalises_and_unquotes():
    from paperbytes.pubmed.query import journal_clause

    # Unquoted; & -> and; stray -- collapsed.
    assert journal_clause("Lancet Diabetes & Endocrinology") == "Lancet Diabetes and Endocrinology[Journal]"
    assert journal_clause("JAMA Otolaryngology-- Head & Neck Surgery") == (
        "JAMA Otolaryngology Head and Neck Surgery[Journal]"
    )
    assert '"' not in journal_clause("New England Journal of Medicine")


def test_species_toggle_adds_only_its_clause():
    on = build_search_term(SearchFilters(**FIXED, restrict_humans=True))
    off = build_search_term(SearchFilters(**FIXED, restrict_humans=False))
    assert "humans[MeSH Terms]" in on
    assert "humans[MeSH Terms]" not in off
    assert "English[Language]" in on and "English[Language]" in off  # neighbour untouched


def test_language_toggle_removes_only_its_clause():
    term = build_search_term(SearchFilters(**FIXED, restrict_english=False, restrict_humans=True))
    assert "English[Language]" not in term
    assert "humans[MeSH Terms]" in term  # neighbour untouched


def test_included_pub_types_toggle():
    term = build_search_term(SearchFilters(**FIXED, use_included_pub_types=False))
    assert "randomizedcontrolledtrial[pt]" not in term


def test_excluded_pub_types_toggle():
    term = build_search_term(SearchFilters(**FIXED, use_excluded_pub_types=False))
    assert " NOT " not in term


def test_multiword_terms_are_quoted():
    term = build_search_term(SearchFilters(**FIXED, mesh_terms=["Heart Failure", "Sepsis"]))
    assert '"Heart Failure"[MeSH Terms]' in term  # quoted
    assert "Sepsis[MeSH Terms]" in term  # single token, unquoted


def test_extra_terms_are_and_ed():
    term = build_search_term(SearchFilters(**FIXED, extra_terms="troponin"))
    assert "AND (troponin)" in term


def test_empty_override_lists_no_dangling_operators():
    term = build_search_term(
        SearchFilters(**FIXED, included_pub_types=[], excluded_pub_types=[])
    )
    assert "()" not in term
    assert not term.rstrip(")").endswith("NOT")
    assert "AND  AND" not in term


def test_describe_term_is_multiline():
    described = describe_term(build_search_term(SearchFilters(**FIXED)))
    assert "\n  AND " in described
    assert "\n  NOT " in described
