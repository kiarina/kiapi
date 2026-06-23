"""The complete contract for one Crawl4AI fetch call.

Built from settings + request by ``resolve_fetch_params``: it carries the
backend address, the Crawl4AI ``/md`` knobs (filter/cache), and the limits
(timeout, concurrency, empty threshold) ``handle_fetch`` needs to issue the
request and judge its result. Nothing here is caller-tunable in this op.
"""

from typing import Literal

from pydantic import BaseModel


class FetchParams(BaseModel):
    url: str
    format: Literal["markdown", "pdf"]

    # Crawl4AI backend base URL.
    base_url: str
    timeout_s: float

    # Crawl4AI /md knobs (ignored for the /pdf format).
    filter: str
    cache: str

    # Empty-result threshold.
    min_content_chars: int
