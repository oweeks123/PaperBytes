from pathlib import Path

import pytest

from paperbytes.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def settings() -> Settings:
    """Settings with an email set (so the client will make requests) and no API
    key (so the rate limit is the 3/s no-key path)."""
    return Settings(pubmed_email="test@example.com", ncbi_api_key=None)


@pytest.fixture
def settings_with_key() -> Settings:
    return Settings(pubmed_email="test@example.com", ncbi_api_key="abc123")
