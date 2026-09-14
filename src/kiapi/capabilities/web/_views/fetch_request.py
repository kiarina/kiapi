"""web fetch request model.

``GET /v1/web/fetch?url=...`` renders one page to readable text (or PDF) via the
Crawl4AI backend. The output ``format`` is chosen by the request's ``Accept``
header at the router and folded in here. Like ``search`` there is no ``mode``;
the router runs it as a synchronous Job on the single worker.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FetchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Absolute http(s) URL of the page to fetch. Passed to Crawl4AI verbatim.
    url: str = Field(..., min_length=1)

    # Resolved from Accept: text/markdown (default) → "markdown",
    # application/pdf → "pdf".
    format: Literal["markdown", "pdf"] = "markdown"

    @field_validator("url")
    @classmethod
    def _require_http_scheme(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must be an absolute http:// or https:// URL")
        return v
