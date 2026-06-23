"""web capability defaults, read from ``KIAPI_WEB_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class WebSettings(BaseSettings):
    """Settings for Web search/fetch backends and request defaults."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_WEB_",
        extra="ignore",
        protected_namespaces=(),
    )

    # --------------------------------------------------
    # search
    # --------------------------------------------------

    search_image: str = Field(
        default="searxng/searxng:latest",
        title="Search backend Docker image",
        description="SearXNG Docker image name launched as the Web search backend.",
    )

    fetch_image: str = Field(
        default="unclecode/crawl4ai:latest",
        title="Fetch backend Docker image",
        description="Crawl4AI Docker image name launched as the Web page fetch backend.",
    )

    backend_ready_timeout_s: float = Field(
        default=60.0,
        title="Backend ready timeout seconds",
        description="Maximum seconds to wait for the search/fetch backend subprocess to become ready.",
    )

    backend_log_dir: str = Field(
        default="/tmp/kiapi/logs/web",
        title="Backend log directory",
        description="Directory where search/fetch backend subprocess logs are written.",
    )

    timeout_s: float = Field(
        default=10.0,
        title="Search timeout seconds",
        description="Maximum seconds allowed for one search request to SearXNG.",
    )

    default_categories: list[str] | None = Field(
        default=None,
        title="Default search categories",
        description=(
            "Categories passed to SearXNG when a request omits categories.\n"
            "When None, SearXNG decides from its own defaults."
        ),
    )

    default_engines: list[str] | None = Field(
        default=None,
        title="Default search engines",
        description=(
            "SearXNG engine names used when a request omits engines.\n"
            "When None, SearXNG decides from its own defaults."
        ),
    )

    default_language: str | None = Field(
        default=None,
        title="Default search language",
        description=(
            "Language code passed to SearXNG when a request omits language.\n"
            "When None, SearXNG decides from its own defaults."
        ),
    )

    default_safesearch: int | None = Field(
        default=None,
        title="Default SafeSearch level",
        description=(
            "SearXNG SafeSearch value used when a request omits safesearch.\n"
            "Typically 0 disables it, 1 is moderate, and 2 is stricter. None "
            "uses the SearXNG default."
        ),
    )

    default_max_results: int | None = Field(
        default=10,
        title="Default maximum search results",
        description=(
            "Maximum number of results returned when a request omits max_results.\n"
            "Set to None to disable client-side truncation in kiapi."
        ),
    )

    # --------------------------------------------------
    # fetch
    # --------------------------------------------------

    fetch_timeout_s: float = Field(
        default=30.0,
        title="Page fetch timeout seconds",
        description="Maximum seconds allowed for one page fetch request to Crawl4AI.",
    )

    fetch_min_content_chars: int = Field(
        default=1,
        title="Minimum fetched content characters",
        description=(
            "Minimum stripped Markdown length before fetched content is treated as empty.\n"
            "With 1, only truly empty renders fail. Higher values also reject "
            "near-empty pages."
        ),
    )

    fetch_filter: str = Field(
        default="fit",
        title="Fetch Markdown filter",
        description=(
            "Body extraction mode for Crawl4AI /md.\n"
            "fit returns readability-pruned Markdown; raw returns Markdown "
            "closer to the full DOM."
        ),
    )

    fetch_cache: str = Field(
        default="0",
        title="Fetch cache-bust value",
        description=(
            "Cache control value passed to Crawl4AI /md.\n"
            "0 lets the server cache normally. Changing the value can act as a "
            "cache-busting identifier."
        ),
    )


settings_manager = SettingsManager(WebSettings)
