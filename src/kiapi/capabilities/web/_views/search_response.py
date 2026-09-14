"""web search response.

SearXNG's JSON is passed through with only the top level typed: the per-result
dicts are forwarded verbatim (``list[dict]``) so SearXNG's evolving fields
(``title``/``url``/``content``/``engine``/``score``/``img_src``/…) reach the
caller without kiapi re-modelling them. ``results`` is truncated to the request's
``max_results``; the auxiliary blocks (``answers``/``infoboxes``/``suggestions``)
are forwarded untruncated because agents find direct answers there.
"""

from typing import Any

from pydantic import BaseModel, Field


class SearchResponse(BaseModel):
    query: str = Field(
        description=(
            "Normalized query returned by SearXNG. This usually matches the "
            "submitted `query`, but SearXNG may normalize whitespace or operators."
        )
    )
    results: list[dict[str, Any]] = Field(
        description=(
            "Search result dictionaries forwarded from SearXNG and truncated by "
            "`max_results`. Common keys include `title`, `url`, `content`, "
            "`engine`, `score`, `img_src`, and `publishedDate`; exact fields "
            "depend on the engine and result type."
        )
    )
    answers: list[Any] = Field(
        description=("Direct-answer blocks from SearXNG, forwarded without truncation.")
    )
    infoboxes: list[Any] = Field(
        description=(
            "Knowledge-panel style infoboxes from SearXNG, forwarded without "
            "truncation."
        )
    )
    suggestions: list[Any] = Field(
        description="Search suggestions from SearXNG, forwarded without truncation."
    )
    unresponsive_engines: list[Any] = Field(
        description=(
            "SearXNG `unresponsive_engines`: engines that failed or timed out for "
            "this query, usually as `[engine, reason]` pairs. Results may still "
            "be usable when this list is non-empty."
        )
    )
