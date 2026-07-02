"""web family — SearXNG search + Crawl4AI fetch as resident subprocess models.

Endpoints: ``POST /v1/web/search`` (metasearch) and ``GET /v1/web/fetch``
(render one page to markdown/PDF). Each backend is loaded as a foreground
``docker run --rm`` subprocess and held resident by the global model cache.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.FetchError import FetchError
    from ._exceptions.SearchBackendError import SearchBackendError
    from ._helpers.register import register
    from ._operations.handle_fetch import handle_fetch
    from ._operations.handle_search import handle_search
    from ._settings import settings_manager
    from ._views.fetch_request import FetchRequest
    from ._views.fetch_result import FetchResult
    from ._views.search_request import SearchRequest
    from ._views.search_response import SearchResponse

__all__ = [
    "FetchError",
    "FetchRequest",
    "FetchResult",
    "SearchBackendError",
    "SearchRequest",
    "SearchResponse",
    "handle_fetch",
    "handle_search",
    "register",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "FetchError": "._exceptions.FetchError",
        "FetchRequest": "._views.fetch_request",
        "FetchResult": "._views.fetch_result",
        "SearchBackendError": "._exceptions.SearchBackendError",
        "SearchRequest": "._views.search_request",
        "SearchResponse": "._views.search_response",
        "handle_fetch": "._operations.handle_fetch",
        "handle_search": "._operations.handle_search",
        "register": "._helpers.register",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
