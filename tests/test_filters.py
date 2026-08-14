from paperbytes.pubmed import filters


def test_curated_journals_loaded_from_bucket_file():
    # The scope is sourced from article_bucket.txt at the backend root.
    journals = filters.CURATED_JOURNALS
    assert len(journals) > 100  # the full clinical bucket, not the old 26
    assert "New England Journal of Medicine" in journals
    assert "BMJ" in journals
    assert "Lancet" in journals


def test_load_curated_journals_strips_and_dedupes(tmp_path):
    f = tmp_path / "bucket.txt"
    f.write_text("  Journal A  \n\nJournal B\nJournal A\n   \n", encoding="utf-8")
    assert filters.load_curated_journals(f) == ("Journal A", "Journal B")


def test_load_curated_journals_missing_file_is_empty(tmp_path):
    assert filters.load_curated_journals(tmp_path / "nope.txt") == ()
