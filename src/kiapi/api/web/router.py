"""Web API (web): ``POST /v1/web/search`` + ``GET /v1/web/fetch``.

``fetch`` selects its output format from the ``Accept`` header (``text/markdown``
default, ``application/pdf``) and returns the rendered page as a raw body, in the
generation families' raw-bytes-by-default style; errors come back as JSON.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import ValidationError as PydanticValidationError

from kiapi.api import (
    REQUIRE_AUTH,
    get_ctx,
    get_worker,
    register_capability_endpoints,
)
from kiapi.api._settings import settings_manager
from kiapi.api.web._views import FetchAPIRequest, FetchErrorResponse
from kiapi.capabilities.web import (
    FetchError,
    FetchRequest,
    SearchBackendError,
    SearchRequest,
    SearchResponse,
    handle_fetch,
    handle_search,
)
from kiapi.core.app import AppContext
from kiapi.core.memory import MemoryBudgetError
from kiapi.core.model import UnknownModelError
from kiapi.core.setup import SetupRequiredError
from kiapi.core.worker import Worker

router = APIRouter(dependencies=REQUIRE_AUTH)


def fetch_api_request(
    url: Annotated[
        str,
        Query(
            min_length=1,
            description=(
                "Absolute http:// or https:// URL of an HTML page to fetch. "
                "Non-HTML resources such as images, audio, video, archives, and "
                "PDFs are rejected with `not_html`."
            ),
            examples=["https://example.com/"],
        ),
    ],
    accept: Annotated[
        str | None,
        Header(
            alias="Accept",
            description=(
                "Requested output media type. application/pdf returns PDF; "
                "text/markdown, text/plain, text/*, */*, browser default "
                "headers, or an omitted header return Markdown. application/json "
                "and other incompatible concrete media types return HTTP 406."
            ),
            examples=["text/markdown", "application/pdf"],
        ),
    ] = None,
) -> FetchAPIRequest:
    return FetchAPIRequest(url=url, accept=accept)


@router.post(
    "/v1/web/search",
    response_model=SearchResponse,
    responses={
        400: {"description": "Unknown web model or invalid model selection."},
        422: {"description": "Request schema or validation error."},
        502: {
            "description": "SearXNG backend was unreachable or returned an HTTP error."
        },
        503: {
            "description": "Backend Docker image is not activated or memory budget is exhausted."
        },
        504: {
            "description": "SearXNG or the sync job exceeded the configured timeout."
        },
    },
)
async def search_web(
    req: SearchRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> dict:
    """Search the live web with SearXNG and return JSON results.

    The request body maps to SearXNG's search parameters. `query` is passed
    through verbatim, so SearXNG inline operators such as `site:`, `!wp`,
    `!images`, and language operators like `:ja` work normally. `format=json` is
    always added by kiapi.

    This endpoint is synchronous from the client's perspective: it waits up to
    `KIAPI_SYNC_TIMEOUT_S` and returns `SearchResponse`. Internally it still
    creates a Job and runs through the single-flight worker so web backends share
    the same queue, setup checks, and resident subprocess lifecycle as other
    capabilities.

    Results are live and non-deterministic. `results` is optionally truncated by
    `max_results`, while `answers`, `infoboxes`, `suggestions`, and
    `unresponsive_engines` are forwarded from SearXNG without truncation.
    """
    settings = settings_manager.get_settings()

    job = ctx.job_store.create(type="web.search", params=req.model_dump(mode="json"))
    fut = await worker.submit(job, lambda: handle_search(ctx, req))

    try:
        return await asyncio.wait_for(fut, timeout=settings.sync_timeout_s)
    except TimeoutError:
        raise HTTPException(  # noqa: B904
            status_code=504,
            detail=f"web.search job {job.id} exceeded sync timeout "
            f"({settings.sync_timeout_s}s); it keeps running - poll /v1/jobs/{job.id}",
        )
    except SearchBackendError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))  # noqa: B904
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except SetupRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except MemoryBudgetError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"web.search failed: {exc}")  # noqa: B904


def _negotiate_format(accept: str | None) -> str | None:
    """Map the Accept header to a fetch format, or None if unacceptable.

    ``application/pdf`` → ``pdf``; markdown/text/wildcard/absent → ``markdown``
    (the default); a concrete incompatible type (e.g. ``application/json``) → None.
    """
    if accept is None:
        return "markdown"
    a = accept.lower()
    if "application/pdf" in a:
        return "pdf"
    if any(t in a for t in ("text/markdown", "text/plain", "text/*", "*/*")):
        return "markdown"
    return None


@router.get(
    "/v1/web/fetch",
    responses={
        200: {
            "description": (
                "Rendered page body. Markdown is returned by default; PDF is "
                "returned when the Accept header allows application/pdf."
            ),
            "content": {
                "text/markdown": {"schema": {"type": "string"}},
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
            },
            "headers": {
                "X-Kiapi-Url": {
                    "description": "Fetched URL recorded on the stored artifact.",
                    "schema": {"type": "string"},
                },
                "X-Kiapi-File-Id": {
                    "description": "Files-API id of the rendered Markdown or PDF artifact.",
                    "schema": {"type": "string"},
                },
                "X-Kiapi-Job-Id": {
                    "description": "Job id created for the fetch operation.",
                    "schema": {"type": "string"},
                },
                "X-Kiapi-Content-Type": {
                    "description": "Detected upstream page Content-Type, when known.",
                    "schema": {"type": "string"},
                },
            },
        },
        406: {
            "model": FetchErrorResponse,
            "description": "Accept header does not allow Markdown or PDF.",
        },
        422: {
            "model": FetchErrorResponse,
            "description": "Invalid URL, non-HTML resource, or empty rendered content.",
        },
        502: {
            "model": FetchErrorResponse,
            "description": "Target URL or Crawl4AI backend was unreachable or returned an HTTP error.",
        },
        503: {
            "description": "Backend Docker image is not activated or memory budget is exhausted."
        },
        504: {
            "description": "Crawl4AI or the sync job exceeded the configured timeout."
        },
    },
)
async def fetch_web(
    api_req: FetchAPIRequest = Depends(fetch_api_request),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Render one HTML page to Markdown or PDF and stream the raw body.

    `url` is supplied as a query parameter. The router resolves the `Accept`
    header to the capability request's internal `format`: `application/pdf`
    selects PDF; Markdown-compatible, text-compatible, wildcard, browser default,
    or omitted Accept headers select Markdown. Incompatible concrete media types
    return HTTP 406 with a structured JSON error.

    Fetch performs a cheap preflight check before rendering. Non-HTML resources
    are rejected with `not_html`; pages that render to no extractable text are
    rejected with `empty_content`. Successful bodies are stored in the Files API
    and streamed back directly with `X-Kiapi-File-Id`, `X-Kiapi-Job-Id`, and
    upstream `X-Kiapi-Content-Type` headers when available.
    """
    settings = settings_manager.get_settings()
    fmt = _negotiate_format(api_req.accept)
    if fmt is None:
        raise HTTPException(
            status_code=406,
            detail={
                "error": "unsupported_accept",
                "message": "Accept must allow text/markdown or application/pdf.",
                "url": api_req.url,
            },
        )

    try:
        req = FetchRequest(url=api_req.url, format=fmt)  # type: ignore[arg-type]
    except PydanticValidationError as exc:
        # Keep the fetch error envelope and stay JSON-serializable: a custom
        # field_validator raises ValueError, whose object pydantic stashes in
        # each error's ``ctx`` — passing exc.errors() straight through would
        # 500 on encoding. Surface the human-readable messages only.
        raise HTTPException(  # noqa: B904
            status_code=422,
            detail={
                "error": "invalid_request",
                "message": "; ".join(e["msg"] for e in exc.errors()),
                "url": api_req.url,
            },
        )

    job = ctx.job_store.create(type="web.fetch", params=req.model_dump(mode="json"))
    fut = await worker.submit(job, lambda: handle_fetch(ctx, req))

    try:
        result = await asyncio.wait_for(fut, timeout=settings.sync_timeout_s)
    except FetchError as exc:
        raise HTTPException(  # noqa: B904
            status_code=exc.status_code,
            detail={
                "error": exc.code,
                "message": str(exc),
                "url": api_req.url,
                "content_type": exc.content_type,
            },
        )
    except TimeoutError:
        raise HTTPException(  # noqa: B904
            status_code=504,
            detail=f"web.fetch job {job.id} exceeded sync timeout "
            f"({settings.sync_timeout_s}s); it keeps running - poll /v1/jobs/{job.id}",
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except SetupRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except MemoryBudgetError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"web.fetch failed: {exc}")  # noqa: B904

    file_id = result["file_id"]
    rec = ctx.file_store.get(file_id)
    if rec is None:
        raise HTTPException(
            status_code=500,
            detail=f"web.fetch produced missing artifact {file_id!r}",
        )

    headers = {
        "X-Kiapi-Url": result["url"],
        "X-Kiapi-File-Id": file_id,
        "X-Kiapi-Job-Id": job.id,
    }
    if result.get("content_type"):
        headers["X-Kiapi-Content-Type"] = result["content_type"]
    return FileResponse(
        rec.path,
        media_type=rec.content_type,
        filename=rec.filename,
        headers=headers,
    )


register_capability_endpoints(router, name="web", base_path="/v1/web")
