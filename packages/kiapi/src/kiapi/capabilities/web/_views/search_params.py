"""The complete contract for one SearXNG search call.

Built from settings + request by ``resolve_search_params``: list fields are
already comma-joined into SearXNG's wire form, and ``max_results`` carries the
resolved truncation limit applied after the page is fetched. Everything needed
to issue the HTTP request and shape the response lives here.
"""

from pydantic import BaseModel


class SearchParams(BaseModel):
    query: str

    # SearXNG wire form: comma-joined strings, or None to omit the parameter.
    categories: str | None
    engines: str | None
    language: str | None
    time_range: str | None
    safesearch: int | None
    pageno: int

    # Client-side truncation limit; None keeps the full page.
    max_results: int | None

    def query_params(self) -> dict:
        """SearXNG ``/search`` querystring (``format=json`` is forced here)."""
        params: dict[str, object] = {
            "q": self.query,
            "format": "json",
            "pageno": self.pageno,
        }
        if self.categories is not None:
            params["categories"] = self.categories
        if self.engines is not None:
            params["engines"] = self.engines
        if self.language is not None:
            params["language"] = self.language
        if self.time_range is not None:
            params["time_range"] = self.time_range
        if self.safesearch is not None:
            params["safesearch"] = self.safesearch
        return params
