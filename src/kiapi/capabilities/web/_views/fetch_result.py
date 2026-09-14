"""web fetch result — the raw body the router streams back.

fetch returns the rendered page directly (not a JSON envelope): ``content`` is
the bytes to write, ``media_type`` the response Content-Type (``text/markdown``
or ``application/pdf``). ``content_type`` is the *upstream* page's MIME (from the
preflight probe), echoed in a response header for visibility. This mirrors the
generation families' raw-bytes-by-default house style.
"""

from pydantic import BaseModel


class FetchResult(BaseModel):
    content: bytes
    media_type: str

    # Final URL after redirects, and the upstream page's detected MIME (or None
    # when the probe could not determine it).
    url: str
    content_type: str | None
