import httpx
import pytest
import respx

from paperbytes.config import Settings
from paperbytes.pubmed.client import (
    PubMedClient,
    PubMedRateLimitError,
    PubMedResponseError,
)
from paperbytes.pubmed.models import JournalScope, SearchFilters

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _articles_xml(*pmids: str) -> bytes:
    records = "".join(
        f"<PubmedArticle><MedlineCitation><PMID>{p}</PMID>"
        f"<Article><Journal><Title>J</Title></Journal>"
        f"<ArticleTitle>Title {p}</ArticleTitle></Article>"
        f"</MedlineCitation></PubmedArticle>"
        for p in pmids
    )
    return f"<PubmedArticleSet>{records}</PubmedArticleSet>".encode()


def _make_client(settings: Settings) -> PubMedClient:
    return PubMedClient(settings, http_client=httpx.AsyncClient(base_url=BASE))


@pytest.mark.asyncio
async def test_esearch_returns_history_handles(settings):
    async with respx.mock(base_url=BASE) as mock:
        mock.get("esearch.fcgi").respond(
            200,
            json={"esearchresult": {"count": "42", "webenv": "WE", "querykey": "1", "idlist": ["1"]}},
        )
        async with _make_client(settings) as client:
            res = await client.esearch("anything")
        assert res.count == 42 and res.webenv == "WE" and res.query_key == "1"


@pytest.mark.asyncio
async def test_efetch_retries_on_429_then_succeeds(settings):
    async with respx.mock(base_url=BASE) as mock:
        route = mock.get("efetch.fcgi")
        route.side_effect = [
            httpx.Response(429),
            httpx.Response(200, content=_articles_xml("1", "2")),
        ]
        async with _make_client(settings) as client:
            arts = await client.efetch(ids=["1", "2"])
        assert route.call_count == 2
        assert [a.pmid for a in arts] == ["1", "2"]


@pytest.mark.asyncio
async def test_non_429_4xx_does_not_retry(settings):
    async with respx.mock(base_url=BASE) as mock:
        route = mock.get("esearch.fcgi").respond(400)
        async with _make_client(settings) as client:
            with pytest.raises(PubMedResponseError):
                await client.esearch("x")
        assert route.call_count == 1  # not retried


@pytest.mark.asyncio
async def test_persistent_429_surfaces_rate_limit_error(settings):
    async with respx.mock(base_url=BASE) as mock:
        mock.get("efetch.fcgi").respond(429)
        async with _make_client(settings) as client:
            with pytest.raises(PubMedRateLimitError):
                await client.efetch(ids=["1"])


@pytest.mark.asyncio
async def test_200_with_empty_result_error_body_is_empty_list(settings):
    async with respx.mock(base_url=BASE) as mock:
        mock.get("efetch.fcgi").respond(
            200, content=b"<eFetchResult><ERROR>Empty result - nothing to do</ERROR></eFetchResult>"
        )
        async with _make_client(settings) as client:
            assert await client.efetch(ids=["1"]) == []


@pytest.mark.asyncio
async def test_200_with_real_error_body_raises(settings):
    async with respx.mock(base_url=BASE) as mock:
        mock.get("efetch.fcgi").respond(
            200, content=b"<eFetchResult><ERROR>API key invalid</ERROR></eFetchResult>"
        )
        async with _make_client(settings) as client:
            with pytest.raises(PubMedResponseError):
                await client.efetch(ids=["1"])


@pytest.mark.asyncio
async def test_large_id_list_uses_post(settings):
    async with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        post_route = mock.post("efetch.fcgi").respond(200, content=_articles_xml("1"))
        get_route = mock.get("efetch.fcgi").respond(200, content=_articles_xml("1"))
        async with _make_client(settings) as client:
            await client.efetch(ids=[str(i) for i in range(250)])
        assert post_route.called and not get_route.called


@pytest.mark.asyncio
async def test_small_id_list_uses_get(settings):
    async with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        post_route = mock.post("efetch.fcgi").respond(200, content=_articles_xml("1"))
        get_route = mock.get("efetch.fcgi").respond(200, content=_articles_xml("1"))
        async with _make_client(settings) as client:
            await client.efetch(ids=["1", "2"])
        assert get_route.called and not post_route.called


@pytest.mark.asyncio
async def test_search_and_fetch_pages_via_history_server():
    # page size 2, count 3 -> two efetch pages (offsets 0 and 2).
    settings = Settings(pubmed_email="test@example.com", pubmed_page_size=2)
    async with respx.mock(base_url=BASE) as mock:
        mock.get("esearch.fcgi").respond(
            200,
            json={"esearchresult": {"count": "3", "webenv": "WE", "querykey": "1", "idlist": []}},
        )
        efetch = mock.get("efetch.fcgi")
        efetch.side_effect = [
            httpx.Response(200, content=_articles_xml("1", "2")),
            httpx.Response(200, content=_articles_xml("3")),
        ]
        async with _make_client(settings) as client:
            # journal_scope=all keeps the term short so esearch stays a GET.
            got = [a.pmid async for a in client.search_and_fetch(SearchFilters(journal_scope=JournalScope.ALL))]
        assert got == ["1", "2", "3"]
        assert efetch.call_count == 2


@pytest.mark.asyncio
async def test_esearch_posts_long_terms(settings):
    long_term = "(" + " OR ".join(f'"Journal Number {i}"[Journal]' for i in range(300)) + ")"
    assert len(long_term) > 2000
    async with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        post = mock.post("esearch.fcgi").respond(
            200, json={"esearchresult": {"count": "1", "webenv": "W", "querykey": "1", "idlist": []}}
        )
        get = mock.get("esearch.fcgi").respond(
            200, json={"esearchresult": {"count": "0", "webenv": "W", "querykey": "1", "idlist": []}}
        )
        async with _make_client(settings) as client:
            res = await client.esearch(long_term)
        assert post.called and not get.called
        assert res.count == 1


@pytest.mark.asyncio
async def test_esearch_gets_short_terms(settings):
    async with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        post = mock.post("esearch.fcgi").respond(200, json={"esearchresult": {"count": "0"}})
        get = mock.get("esearch.fcgi").respond(
            200, json={"esearchresult": {"count": "5", "webenv": "W", "querykey": "1", "idlist": []}}
        )
        async with _make_client(settings) as client:
            res = await client.esearch("short term")
        assert get.called and not post.called
        assert res.count == 5


@pytest.mark.asyncio
async def test_missing_email_fails_fast(settings):
    from paperbytes.pubmed.client import PubMedError

    no_email = Settings(pubmed_email=None)
    async with _make_client(no_email) as client:
        with pytest.raises(PubMedError):
            await client.esearch("x")


def test_rate_limit_derives_from_key():
    assert Settings(pubmed_email="e@x.com").ncbi_rate_limit == 3
    assert Settings(pubmed_email="e@x.com", ncbi_api_key="k").ncbi_rate_limit == 10
