"""Merge a fetch request with settings defaults into the complete FetchParams."""

from .._settings import WebSettings
from .._views.fetch_params import FetchParams
from .._views.fetch_request import FetchRequest


def resolve_fetch_params(
    settings: WebSettings,
    req: FetchRequest,
    *,
    base_url: str,
    api_token: str | None = None,
) -> FetchParams:
    return FetchParams(
        url=req.url,
        format=req.format,
        base_url=base_url,
        api_token=api_token,
        timeout_s=settings.fetch_timeout_s,
        filter=settings.fetch_filter,
        cache=settings.fetch_cache,
        min_content_chars=settings.fetch_min_content_chars,
    )
