"""Async NCBI E-utilities client.

Replaces the synchronous ``pymed`` retrieval. Holds one shared
``httpx.AsyncClient``, enforces NCBI's rate policy client-side, retries transient
failures, and pages large result sets through the history server so callers never
hold the whole set in memory or build enormous URLs.

Settings are injected — no module-level globals — so tests can supply their own
transport and config.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ..config import Settings
from .models import PubMedArticle, SearchFilters
from .parser import XmlErrorResponse, parse_efetch_xml, raise_for_xml_error
from .query import build_search_term, describe_term

log = structlog.get_logger("paperbytes.pubmed")

_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
# Above this many explicit IDs, EFetch must use POST — GET URLs get too long.
_POST_ID_THRESHOLD = 200
# Above this term length (chars), ESearch must POST — a large journal OR-group
# (hundreds of "title"[Journal] clauses) blows past practical GET URL limits.
_POST_TERM_THRESHOLD = 2000


class PubMedError(Exception):
    """Base class for all retrieval-layer failures."""


class PubMedRateLimitError(PubMedError):
    """NCBI returned HTTP 429. Retried with backoff; surfaced if it persists."""


class PubMedResponseError(PubMedError):
    """A non-retryable bad response (4xx other than 429, or a 200 ``<ERROR>`` body)."""


class _RetryableServerError(PubMedError):
    """Internal: a 5xx worth retrying. Never escapes the client."""


@dataclass(slots=True)
class ESearchResult:
    count: int
    webenv: str | None
    query_key: str | None
    idlist: list[str] = field(default_factory=list)


class _RateLimiter:
    """Monotonic-clock request spacing plus a concurrency semaphore.

    NCBI allows 10 req/s with an API key and 3/s without; exceeding it gets the
    caller's IP throttled. We space requests by ``1/rate`` seconds using the event
    loop clock (never ``time.sleep``, which would block the loop) and cap
    in-flight requests with a semaphore sized to the rate.
    """

    def __init__(self, rate_per_sec: int) -> None:
        self._interval = 1.0 / rate_per_sec
        self._lock = asyncio.Lock()
        self._next_at = 0.0
        self.semaphore = asyncio.Semaphore(rate_per_sec)

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            now = loop.time()
            delay = self._next_at - now
            if delay > 0:
                await asyncio.sleep(delay)
                now = loop.time()
            self._next_at = max(now, self._next_at) + self._interval


class PubMedClient:
    """Async client for ESearch/EFetch against NCBI E-utilities."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=_BASE_URL, timeout=settings.pubmed_timeout_seconds
        )
        self._limiter = _RateLimiter(settings.ncbi_rate_limit)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> PubMedClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # -- request plumbing --------------------------------------------------
    def _common_params(self) -> dict[str, str]:
        """tool + email (+ api_key) — required by NCBI's usage policy. Email is
        checked here so retrieval fails fast when it is unconfigured, without
        preventing the app from booting for credential-free read endpoints."""
        if not self._settings.pubmed_email:
            raise PubMedError("PUBMED_EMAIL is not configured; required for NCBI requests")
        params = {"tool": self._settings.ncbi_tool, "email": self._settings.pubmed_email}
        if self._settings.ncbi_api_key:
            params["api_key"] = self._settings.ncbi_api_key
        return params

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Issue a rate-limited request, retrying 429/5xx with exponential
        backoff + jitter (capped at 5 attempts). 4xx (other than 429) do not
        retry. The ``<ERROR>``-body case is handled by callers via
        :func:`raise_for_xml_error`."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((PubMedRateLimitError, _RetryableServerError)),
            stop=stop_after_attempt(5),
            wait=wait_exponential_jitter(initial=1, max=30),
            reraise=True,
        ):
            with attempt:
                await self._limiter.wait()
                async with self._limiter.semaphore:
                    resp = await self._http.request(method, path, params=params, data=data)
                if resp.status_code == 429:
                    raise PubMedRateLimitError("NCBI rate limit hit (429)")
                if resp.status_code >= 500:
                    raise _RetryableServerError(f"NCBI server error ({resp.status_code})")
                if resp.status_code >= 400:
                    raise PubMedResponseError(f"NCBI returned HTTP {resp.status_code}")
                return resp
        raise PubMedError("unreachable: retry loop exited without returning")  # pragma: no cover

    # -- E-utilities calls -------------------------------------------------
    async def esearch(self, term: str, *, retmax: int = 0, retstart: int = 0) -> ESearchResult:
        """Call ``esearch.fcgi`` with ``usehistory=y`` so the result set lands on
        the history server; returns count + WebEnv/QueryKey for paged fetching."""
        params = {
            **self._common_params(),
            "db": "pubmed",
            "retmode": "json",
            "usehistory": "y",
            "term": term,
            "retmax": str(retmax),
            "retstart": str(retstart),
        }
        # A large journal OR-group makes the term too long for a GET URL; NCBI
        # accepts the identical parameters via POST.
        if len(term) > _POST_TERM_THRESHOLD:
            resp = await self._request("POST", "esearch.fcgi", data=params)
        else:
            resp = await self._request("GET", "esearch.fcgi", params=params)
        result = resp.json().get("esearchresult", {})
        if "ERROR" in result:
            raise PubMedResponseError(f"ESearch error: {result['ERROR']}")
        return ESearchResult(
            count=int(result.get("count", 0)),
            webenv=result.get("webenv"),
            query_key=result.get("querykey"),
            idlist=result.get("idlist", []),
        )

    async def efetch(
        self,
        *,
        ids: list[str] | None = None,
        webenv: str | None = None,
        query_key: str | None = None,
        retstart: int = 0,
        retmax: int | None = None,
        include_raw: bool = False,
    ) -> list[PubMedArticle]:
        """Fetch and parse records, either from an explicit ID list or from the
        history server. Uses POST once an explicit ID list exceeds ~200 IDs."""
        base = {
            **self._common_params(),
            "db": "pubmed",
            "retmode": "xml",
            "rettype": "abstract",
        }
        if retmax is not None:
            base["retmax"] = str(retmax)

        method = "GET"
        params: dict[str, str] = dict(base)
        data: dict[str, str] | None = None
        if webenv and query_key:
            params.update({"WebEnv": webenv, "query_key": query_key, "retstart": str(retstart)})
        elif ids:
            if len(ids) > _POST_ID_THRESHOLD:
                # Large ID lists go in the POST body to avoid an over-long URL.
                method, data, params = "POST", {**base, "id": ",".join(ids)}, {}
            else:
                params["id"] = ",".join(ids)
        else:
            raise PubMedError("efetch requires either ids or webenv/query_key")

        resp = await self._request(method, "efetch.fcgi", params=params, data=data)
        try:
            raise_for_xml_error(resp.content)
        except XmlErrorResponse as e:
            # NCBI returns an <ERROR> body with this message when the requested
            # page of a history set holds no records; treat as an empty page
            # rather than a hard failure. Any other <ERROR> is a real problem.
            if "empty result" in str(e).lower():
                return []
            raise PubMedResponseError(str(e)) from e
        return parse_efetch_xml(resp.content, include_raw=include_raw)

    # -- composed helpers --------------------------------------------------
    async def search(self, spec: SearchFilters) -> tuple[str, ESearchResult]:
        """Resolve the term and run the search, returning both so callers can
        report the exact query sent to NCBI."""
        term = build_search_term(spec, default_lookback_days=self._settings.lookback_days)
        result = await self.esearch(term)
        log.info(
            "pubmed.search",
            term=term,
            described=describe_term(term),
            count=result.count,
        )
        return term, result

    async def fetch_page(
        self, result: ESearchResult, *, offset: int, size: int, include_raw: bool = False
    ) -> list[PubMedArticle]:
        """Fetch a single page from an existing search's history-server handle."""
        return await self.efetch(
            webenv=result.webenv,
            query_key=result.query_key,
            retstart=offset,
            retmax=size,
            include_raw=include_raw,
        )

    async def search_and_fetch(
        self, spec: SearchFilters, *, max_results: int | None = None, include_raw: bool = False
    ) -> AsyncIterator[PubMedArticle]:
        """Run a search and yield parsed articles page by page via the history
        server, so callers never hold the whole set in memory. This is the seam
        the fetch/summarise pipeline consumes."""
        term, result = await self.search(spec)
        total = result.count if max_results is None else min(result.count, max_results)
        page = self._settings.pubmed_page_size
        for offset in range(0, total, page):
            size = min(page, total - offset)
            for article in await self.fetch_page(
                result, offset=offset, size=size, include_raw=include_raw
            ):
                yield article
