import pytest

from paperbytes.pubmed.models import to_storage_fields
from paperbytes.pubmed.parser import (
    XmlErrorResponse,
    parse_efetch_xml,
    raise_for_xml_error,
)

from .conftest import load_fixture


@pytest.fixture
def articles():
    parsed = parse_efetch_xml(load_fixture("efetch_sample.xml"))
    return {a.pmid: a for a in parsed}


def test_all_records_parsed(articles):
    assert set(articles) == {"1001", "1002", "1003", "1004", "1005"}


def test_structured_abstract_preserves_labels(articles):
    a = articles["1001"]
    labels = [s.label for s in a.abstract_sections]
    assert labels == ["BACKGROUND", "METHODS", "RESULTS", "CONCLUSIONS"]
    # Flattened form keeps every section.
    assert "BACKGROUND:" in a.abstract and "CONCLUSIONS:" in a.abstract


def test_inline_markup_not_truncated(articles):
    # Title has <i> and <sup>; text after the inline tag must survive.
    assert articles["1001"].title == "Effect of drug X on outcomes2"
    # <sub> tail inside a RESULTS section.
    results = next(s for s in articles["1001"].abstract_sections if s.label == "RESULTS")
    assert "0.05" in results.text
    # Unlabelled markup-heavy abstract keeps all tail text.
    e = articles["1005"].abstract
    assert "3rd highest" in e and "baseline" in e and "102" in e


def test_doi_prefers_article_id_list(articles):
    assert articles["1001"].doi == "10.1000/preferred"


def test_doi_falls_back_to_elocation(articles):
    assert articles["1004"].doi == "10.1000/eloc-only"


def test_no_abstract_is_none(articles):
    a = articles["1002"]
    assert a.abstract is None
    assert a.abstract_sections == []


def test_partial_year_only_date(articles):
    d = articles["1003"].publication_date
    assert d is not None
    assert d.year == 2026 and d.month is None and d.day is None
    assert str(d) == "2026"


def test_full_date_and_entrez_date(articles):
    a = articles["1001"]
    assert str(a.publication_date) == "2026/08/05"
    assert str(a.entrez_date) == "2026/08/10"


def test_mesh_major_topic_flag(articles):
    mesh = {m.term: m.major_topic for m in articles["1001"].mesh_terms}
    assert mesh == {"Heart Failure": True, "Humans": False}


def test_authors_including_collective(articles):
    names = [au.name for au in articles["1001"].authors]
    assert names == ["Jane Smith", "The TRIAL Group"]
    assert articles["1001"].authors[0].affiliation == "Oxford"


def test_publication_types_and_language(articles):
    assert articles["1001"].publication_types == ["Randomized Controlled Trial"]
    assert articles["1001"].language == "eng"


def test_to_storage_fields_maps_onto_orm_columns(articles):
    fields = to_storage_fields(articles["1001"])
    assert fields["pubmed_id"] == "1001"
    assert fields["publication_date"] == "2026/08/05"
    assert fields["journal"] == "The New England Journal of Medicine"
    assert fields["pubmed_url"] == "https://pubmed.ncbi.nlm.nih.gov/1001/"
    assert "BACKGROUND:" in fields["abstract"]
    # keys match exactly the non-summary Article columns
    assert set(fields) == {"pubmed_id", "title", "abstract", "publication_date", "journal", "pubmed_url"}


def test_raise_for_xml_error_detects_error_body():
    with pytest.raises(XmlErrorResponse):
        raise_for_xml_error(load_fixture("efetch_error.xml"))


def test_raise_for_xml_error_ignores_valid_body():
    # A normal article set must not raise.
    raise_for_xml_error(load_fixture("efetch_sample.xml"))


def test_empty_content_parses_to_empty_list():
    assert parse_efetch_xml(b"") == []
