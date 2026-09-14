from kiapi.capabilities.web._operations.resolve_fetch_params import (
    resolve_fetch_params,
)
from kiapi.capabilities.web._settings import WebSettings
from kiapi.capabilities.web._views.fetch_request import FetchRequest


def test_resolve_fetch_params_carries_request_and_settings() -> None:
    settings = WebSettings(
        fetch_timeout_s=12.5,
        fetch_min_content_chars=3,
        fetch_filter="raw",
        fetch_cache="9",
    )
    req = FetchRequest(url="https://example.com", format="pdf")

    params = resolve_fetch_params(settings, req, base_url="http://crawl:8052")

    assert params.url == "https://example.com"
    assert params.format == "pdf"
    assert params.base_url == "http://crawl:8052"
    assert params.timeout_s == 12.5
    assert params.min_content_chars == 3
    assert params.filter == "raw"
    assert params.cache == "9"


def test_resolve_fetch_params_defaults() -> None:
    params = resolve_fetch_params(
        WebSettings(),
        FetchRequest(url="https://a.test"),
        base_url="http://crawl.local",
    )

    # fit_markdown is the chosen default content filter.
    assert params.format == "markdown"
    assert params.filter == "fit"
    assert params.base_url == "http://crawl.local"
