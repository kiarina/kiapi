"""web family — SearXNG search + Crawl4AI fetch as resident subprocess models.

Endpoints: ``POST /v1/web/search`` (metasearch) and ``GET /v1/web/fetch``
(render one page to markdown/PDF). Each backend is loaded as a foreground
``docker run --rm`` subprocess and held resident by the global model cache.
"""

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
    "FetchError",  # ._exceptions
    "FetchRequest",  # ._views
    "FetchResult",  # ._views
    "SearchBackendError",  # ._exceptions
    "SearchRequest",  # ._views
    "SearchResponse",  # ._views
    "handle_fetch",  # ._operations
    "handle_search",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
]
