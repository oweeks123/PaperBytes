from paperbytes.pdf import build_summary_pdf

SAMPLE = {
    "pmid": "40012345",
    "title": "Drug X versus placebo for outcome Y: a randomised trial",
    "journal": "The Lancet",
    "authors": ["Jane Smith", "John Doe", "A Third", "B Fourth", "C Fifth", "D Sixth", "E Seventh"],
    "publication_date": "2026/08",
    "doi": "10.1000/example",
    "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/40012345/",
    "summary": "A concise 50-word summary of the study aim and findings.",
    "specialties": ["Cardiology", "Emergency Medicine"],
    "appraisal": {
        "study_design": "Randomised controlled trial",
        "population": "1,240 adults across 12 UK centres",
        "intervention": "Drug X 50mg once daily",
        "comparator": "Placebo",
        "risk_of_bias": "Low",
        "level_of_evidence": "1b",
        "limitations": "Open-label outcome assessment",
        "outcomes": [
            {"name": "30-day mortality", "measure": "HR", "value": "0.82", "confidence_interval": "0.70-0.96", "p_value": "0.01"},
            {"name": "Major bleeding", "measure": "RR", "value": "1.15", "confidence_interval": "0.90-1.47", "p_value": "0.25"},
        ],
    },
}


def test_build_summary_pdf_returns_pdf_bytes():
    pdf = build_summary_pdf(SAMPLE)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_build_summary_pdf_handles_empty_appraisal():
    minimal = {
        "pmid": "1",
        "title": "Untitled",
        "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/1/",
        "summary": "s",
        "specialties": [],
        "appraisal": {},
    }
    assert build_summary_pdf(minimal)[:5] == b"%PDF-"


def test_build_summary_pdf_without_outcomes():
    data = {**SAMPLE, "appraisal": {**SAMPLE["appraisal"], "outcomes": []}}
    assert build_summary_pdf(data)[:5] == b"%PDF-"


def test_build_summary_pdf_missing_optional_fields():
    # No journal/authors/doi — should still render.
    data = {
        "pmid": "2",
        "title": "Sparse record",
        "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/2/",
        "summary": "s",
        "specialties": ["General medicine"],
        "appraisal": SAMPLE["appraisal"],
    }
    assert build_summary_pdf(data)[:5] == b"%PDF-"
