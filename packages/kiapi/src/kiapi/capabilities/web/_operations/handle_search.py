"""web search service entry, run on the single worker thread."""

import httpx

from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._exceptions.SearchBackendError import SearchBackendError
from .._settings import settings_manager
from .._views.search_request import SearchRequest
from .._views.search_response import SearchResponse
from .resolve_search_params import resolve_search_params


def handle_search(
    ctx: AppContext, req: SearchRequest
) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("web", "search")
    ctx.ensure_model_ready(spec)
    backend = ctx.memory_manager.acquire(spec)
    params = resolve_search_params(settings, req)

    url = f"{backend.base_url.rstrip('/')}/search"  # type: ignore[attr-defined]
    try:
        with httpx.Client(timeout=settings.timeout_s) as client:
            resp = client.get(url, params=params.query_params())
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise SearchBackendError(
            f"SearXNG timed out after {settings.timeout_s}s", status_code=504
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise SearchBackendError(
            f"SearXNG returned HTTP {exc.response.status_code}", status_code=502
        ) from exc
    except httpx.HTTPError as exc:
        raise SearchBackendError(
            f"SearXNG unreachable at {url}: {exc}", status_code=502
        ) from exc

    results = data.get("results", [])
    if params.max_results is not None:
        results = results[: params.max_results]

    return SearchResponse(
        query=data.get("query", req.query),
        results=results,
        answers=data.get("answers", []),
        infoboxes=data.get("infoboxes", []),
        suggestions=data.get("suggestions", []),
        unresponsive_engines=data.get("unresponsive_engines", []),
    ).model_dump(), []
