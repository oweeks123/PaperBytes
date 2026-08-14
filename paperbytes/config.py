"""Application settings via ``pydantic-settings``.

Replaces the scattered ``os.environ`` reads in ``main.py`` with a single typed
``Settings`` object. Every environment variable name the app already used is
preserved (case-insensitive), so existing ``.env`` files and deployment configs
keep working; the only additions are the NCBI E-utilities knobs.

Deviation from the spec, deliberately flagged: the spec asks for ``PUBMED_EMAIL``
to be *required, failing fast at startup*. That directly conflicts with the other
hard constraint that the read-only endpoints (``/articles``, ``/specialties``)
must keep booting without any credentials. We resolve in favour of preserving the
credential-free boot: ``pubmed_email`` is optional here, and the ``PubMedClient``
raises fast the moment retrieval is actually attempted (surfaced as the existing
``400`` on ``/fetch`` and ``/search``). Same fail-fast guarantee, without breaking
the read path.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- NCBI / PubMed -----------------------------------------------------
    # Contact email required by NCBI's usage policy. Optional at boot (see the
    # module docstring); required at the point of retrieval.
    pubmed_email: str | None = None
    # Optional API key. Its presence raises the allowed request rate 3 -> 10/s.
    ncbi_api_key: str | None = None
    # Identifies the client to NCBI, also required by their policy.
    ncbi_tool: str = "PaperBytes"
    # EFetch/ESearch page size; also the threshold for history-server paging.
    pubmed_page_size: int = 100
    pubmed_timeout_seconds: float = 20.0

    # --- Anthropic / summarisation ----------------------------------------
    # Owned by main.py's summarise(); surfaced here so all config lives together.
    anthropic_api_key: str | None = None
    claude_model: str = "claude-haiku-4-5"
    # When true, the /random appraisal is filled from article metadata instead of
    # calling Anthropic — lets the UI be demoed/designed without API credits.
    # Mock results are not treated as a real cache entry, so turning this off
    # (once credits exist) transparently swaps in real AI analysis.
    mock_analysis: bool = False

    # --- AI illustration (OpenAI images) -----------------------------------
    # Optional; without a key the card uses the placeholder art.
    openai_api_key: str | None = None
    image_quality: str = "medium"  # low | medium | high (gpt-image-1)

    # --- Contact form ------------------------------------------------------
    # Destination for contact messages — kept server-side, never sent to the
    # browser. SMTP creds are optional: without them, messages are stored in the
    # contact_messages table instead of emailed.
    contact_email: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None

    # --- Fetch window ------------------------------------------------------
    lookback_days: int = 7

    # --- Storage -----------------------------------------------------------
    database_url: str = "sqlite:///./paperbytes.db"

    # --- Server ------------------------------------------------------------
    port: int = 8000
    reload: bool = False

    # --- Logging -----------------------------------------------------------
    log_level: str = "INFO"

    @property
    def ncbi_rate_limit(self) -> int:
        """Requests/second NCBI permits: 10 with an API key, 3 without."""
        return 10 if self.ncbi_api_key else 3

    @property
    def normalised_database_url(self) -> str:
        """Normalise Heroku-style ``postgres://`` to the ``postgresql://`` scheme
        SQLAlchemy expects. Mirrors the existing behaviour in ``main.py``."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the whole app shares one ``Settings`` instance.

    Exposed as a FastAPI dependency in ``main.py``; tests override it via
    ``app.dependency_overrides``.
    """
    return Settings()
