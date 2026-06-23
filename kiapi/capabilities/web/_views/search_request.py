"""web search request model.

A thin wrapper over SearXNG's ``/search`` query parameters. ``query`` is passed
through verbatim, so SearXNG's inline operators (``!images``, ``!wp``, ``:ja``,
``site:``) work unchanged. ``format=json`` is added internally and is not a
caller concern. There is no ``mode``: web search is run as a synchronous Job on
the single worker.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Search query passed to SearXNG as-is. SearXNG inline operators "
            "work here, for example `site:github.com kiapi`, `!wp Python`, "
            "`!images cat`, or `:ja mlx`."
        ),
        examples=["site:github.com kiarina kiapi"],
    )

    categories: list[str] | None = Field(
        default=None,
        description=(
            "SearXNG categories to search. Omit to use "
            "`KIAPI_WEB_DEFAULT_CATEGORIES`; if that is unset, SearXNG chooses "
            "its own default. Common values include `general`, `it`, `science`, "
            "`news`, `images`, `videos`, `map`, `music`, `files`, and "
            "`social_media`."
        ),
        examples=[["general"], ["it", "science"]],
    )
    engines: list[str] | None = Field(
        default=None,
        description=(
            "Specific SearXNG engines to use. Omit to use "
            "`KIAPI_WEB_DEFAULT_ENGINES`; if that is unset, SearXNG selects "
            "engines from the requested categories. Examples: `google`, `bing`, "
            "`duckduckgo`, `github`, `wikipedia`, `arxiv`."
        ),
        examples=[["duckduckgo"], ["github", "stackoverflow"]],
    )

    language: str | None = Field(
        default=None,
        description=(
            "Optional SearXNG language code such as `ja`, `en`, or `en-US`. "
            "Omit to use `KIAPI_WEB_DEFAULT_LANGUAGE`."
        ),
        examples=["ja", "en"],
    )
    time_range: Literal["day", "week", "month", "year"] | None = Field(
        default=None,
        description=(
            "Optional freshness filter. Supported values are `day`, `week`, "
            "`month`, and `year`. Support depends on the selected engines."
        ),
    )
    safesearch: Literal[0, 1, 2] | None = Field(
        default=None,
        description=(
            "SearXNG safe-search level: `0` disables filtering, `1` is moderate, "
            "and `2` is strict. Omit to use `KIAPI_WEB_DEFAULT_SAFESEARCH`."
        ),
    )

    page: int = Field(
        default=1,
        ge=1,
        description=(
            "One-based SearXNG result page (`pageno`). kiapi fetches exactly one "
            "page per request; increase this value to request the next page."
        ),
    )

    max_results: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Maximum number of `results` to keep from the returned SearXNG page. "
            "SearXNG has no native max-results parameter, so kiapi truncates "
            "client-side. Omit to use `KIAPI_WEB_DEFAULT_MAX_RESULTS`; set the "
            "server default to null to keep the full page."
        ),
        examples=[5, 10],
    )
