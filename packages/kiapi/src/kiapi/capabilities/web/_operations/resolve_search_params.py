"""Merge a search request with settings defaults into the complete SearchParams."""

from .._settings import WebSettings
from .._views.search_params import SearchParams
from .._views.search_request import SearchRequest


def _join(values: list[str] | None) -> str | None:
    """SearXNG takes categories/engines as a comma-separated string."""
    return ",".join(values) if values else None


def resolve_search_params(settings: WebSettings, req: SearchRequest) -> SearchParams:
    categories = (
        req.categories if req.categories is not None else settings.default_categories
    )
    engines = req.engines if req.engines is not None else settings.default_engines

    return SearchParams(
        query=req.query,
        categories=_join(categories),
        engines=_join(engines),
        language=req.language
        if req.language is not None
        else settings.default_language,
        time_range=req.time_range,
        safesearch=req.safesearch
        if req.safesearch is not None
        else settings.default_safesearch,
        pageno=req.page,
        max_results=req.max_results
        if req.max_results is not None
        else settings.default_max_results,
    )
