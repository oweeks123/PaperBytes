"""PubMed retrieval layer.

Fetches a hard-filtered candidate set from NCBI E-utilities and normalises the
EFetch XML into typed :class:`~paperbytes.pubmed.models.PubMedArticle` objects.
Retrieval and parsing only — no summarisation, scoring, or LLM calls. Later
layers consume :meth:`PubMedClient.search_and_fetch`.
"""
