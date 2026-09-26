import httpx

from kiapi.core.app import AppContext
from kiapi.core.model import model_registry

from .._exceptions.SearchBackendError import SearchBackendError
from .._settings import settings_manager
from .._views.search_options import SearchOptions


def list_search_options(ctx: AppContext) -> SearchOptions:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("web", "search")
    ctx.ensure_model_ready(spec)
    backend = ctx.memory_manager.acquire(spec)
    url = f"{backend.base_url.rstrip('/')}/config"  # type: ignore[attr-defined]
    try:
        response = httpx.get(url, timeout=settings.timeout_s)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise SearchBackendError(
            f"SearXNG options unavailable: {exc}", status_code=502
        ) from exc

    return SearchOptions(
        categories=data["categories"],
        engines=sorted(
            (engine["name"] for engine in data["engines"] if engine["enabled"]),
            key=str.casefold,
        ),
    )
