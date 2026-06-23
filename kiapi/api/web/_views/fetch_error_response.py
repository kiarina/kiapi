from pydantic import BaseModel, Field


class _FetchErrorDetail(BaseModel):
    error: str = Field(
        description=(
            "Stable error code such as `unsupported_accept`, `invalid_request`, "
            "`not_html`, `empty_content`, or `fetch_failed`."
        )
    )
    message: str = Field(description="Human-readable error detail.")
    url: str = Field(description="URL submitted to `/v1/web/fetch`.")
    content_type: str | None = Field(
        default=None,
        description=(
            "Detected upstream Content-Type when known. Present for non-HTML "
            "resources and some fetch failures."
        ),
    )


class FetchErrorResponse(BaseModel):
    detail: _FetchErrorDetail = Field(
        description="Structured fetch error payload returned by FastAPI."
    )
