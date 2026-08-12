"""Validate the journal scope in ``article_bucket.txt`` against PubMed.

Each title is queried against PubMed's ``[Journal]`` field. A title that returns
zero all-time results is one PubMed does not recognise (wrong/variant spelling, or
a title it does not index under that name) — it silently contributes nothing to a
search, so it is worth correcting in the file.

Usage:
    PUBMED_EMAIL=you@example.com ./.venv/Scripts/python.exe validate_journals.py
"""

from __future__ import annotations

import asyncio

from paperbytes.config import Settings
from paperbytes.pubmed import filters
from paperbytes.pubmed.client import PubMedClient
from paperbytes.pubmed.query import journal_clause


async def _count(client: PubMedClient, title: str) -> tuple[str, int]:
    """All-time PubMed count for this title in the [Journal] field, using the same
    normalised, unquoted clause the query builder emits."""
    term = journal_clause(title)
    try:
        res = await client.esearch(term)
        return title, res.count
    except Exception as e:  # noqa: BLE001 — report the failure, don't abort the run
        print(f"  ! error for {title!r}: {e}")
        return title, -1


async def main() -> None:
    settings = Settings()
    if not settings.pubmed_email:
        raise SystemExit("Set PUBMED_EMAIL (and optionally NCBI_API_KEY) first.")

    journals = filters.CURATED_JOURNALS
    print(f"Validating {len(journals)} journals from {filters.JOURNAL_LIST_FILE.name} "
          f"at {settings.ncbi_rate_limit} req/s...\n")

    async with PubMedClient(settings) as client:
        results = await asyncio.gather(*(_count(client, j) for j in journals))

    unmatched = [t for t, c in results if c == 0]
    errored = [t for t, c in results if c < 0]
    matched = len(journals) - len(unmatched) - len(errored)

    print(f"\nRecognised: {matched}/{len(journals)}")
    if unmatched:
        print(f"\nNOT RECOGNISED ({len(unmatched)}) — PubMed returns 0 for these titles:")
        for t in unmatched:
            print(f"  - {t}")
    if errored:
        print(f"\nErrored ({len(errored)}): {errored}")
    if not unmatched and not errored:
        print("\nAll titles resolved. ✅")


if __name__ == "__main__":
    asyncio.run(main())
