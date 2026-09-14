"""web fetch service: render one page to readable markdown (or PDF) via Crawl4AI.

Flow:

1. **Preflight probe** (cheap ``HEAD``) → reachability + the upstream MIME. A
   connection failure here is ``fetch_failed``; a non-HTML MIME is rejected as
   ``not_html`` *before* paying for a browser render.
2. **Render** through Crawl4AI ``/md`` (``f=fit`` -> readability-pruned
   fit_markdown) or ``/pdf``.
3. **Empty guard** → a render that produced no content is ``empty_content``.
"""

import base64

import httpx

from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._exceptions.FetchError import FetchError
from .._settings import settings_manager
from .._views.fetch_params import FetchParams
from .._views.fetch_request import FetchRequest
from .._views.fetch_result import FetchResult
from .resolve_fetch_params import resolve_fetch_params

# Content types fetch treats as a renderable page. Anything else (image/audio/
# video/pdf/octet-stream/...) carries no extractable text and is rejected.
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})


def _probe_content_type(params: FetchParams) -> str | None:
    """HEAD the target for reachability + MIME; None if the server omits it."""
    try:
        with httpx.Client(timeout=params.timeout_s, follow_redirects=True) as client:
            resp = client.head(params.url)
    except httpx.HTTPError as exc:
        raise FetchError(
            "fetch_failed",
            f"Could not reach {params.url}: {exc}",
            status_code=502,
        ) from exc

    ct = resp.headers.get("content-type")
    return ct.split(";")[0].strip().lower() if ct else None


def _post_crawl4ai(params: FetchParams, path: str, payload: dict) -> dict:
    url = f"{params.base_url.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=params.timeout_s) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data: dict = resp.json()
            return data
    except httpx.TimeoutException as exc:
        raise FetchError(
            "fetch_failed",
            f"Crawl4AI timed out after {params.timeout_s}s",
            status_code=504,
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise FetchError(
            "fetch_failed",
            f"Crawl4AI returned HTTP {exc.response.status_code}",
            status_code=502,
        ) from exc
    except httpx.HTTPError as exc:
        raise FetchError(
            "fetch_failed",
            f"Crawl4AI unreachable at {params.base_url}: {exc}",
            status_code=502,
        ) from exc


def _render(params: FetchParams) -> tuple[bytes, str, bool]:
    """Return (body, media_type, is_empty) for the requested format."""
    if params.format == "pdf":
        data = _post_crawl4ai(params, "/pdf", {"url": params.url})
        b64 = data.get("pdf") or ""
        body = base64.b64decode(b64) if b64 else b""
        return body, "application/pdf", len(body) == 0

    payload = {"url": params.url, "f": params.filter, "c": params.cache}
    data = _post_crawl4ai(params, "/md", payload)
    markdown = data.get("markdown") or ""
    is_empty = len(markdown.strip()) < params.min_content_chars
    return markdown.encode("utf-8"), "text/markdown; charset=utf-8", is_empty


def handle_fetch(ctx: AppContext, req: FetchRequest) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("web", "fetch")
    ctx.ensure_model_ready(spec)
    backend = ctx.memory_manager.acquire(spec)
    params = resolve_fetch_params(
        settings,
        req,
        base_url=backend.base_url,  # type: ignore[attr-defined]
    )

    content_type = _probe_content_type(params)
    if content_type is not None and content_type not in _HTML_TYPES:
        raise FetchError(
            "not_html",
            f"Resource is not an HTML page (content-type: {content_type}).",
            status_code=422,
            content_type=content_type,
        )

    body, media_type, is_empty = _render(params)

    if is_empty:
        raise FetchError(
            "empty_content",
            "The page was fetched but produced no extractable content.",
            status_code=422,
            content_type=content_type,
        )

    result = FetchResult(
        content=body,
        media_type=media_type,
        url=params.url,
        content_type=content_type,
    )
    suffix = ".pdf" if req.format == "pdf" else ".md"
    rec = ctx.file_store.put_bytes(
        result.content,
        filename=f"fetch{suffix}",
        content_type=result.media_type,
        meta={"url": result.url, "content_type": result.content_type},
    )
    return (
        {
            "file_id": rec.file_id,
            "url": result.url,
            "content_type": result.content_type,
            "media_type": result.media_type,
            "bytes": rec.size,
        },
        [rec.file_id],
    )
