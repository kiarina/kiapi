import urllib.request
from http.client import HTTPResponse
from typing import IO, Any

from .verify_public_url import verify_public_url


class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    # urllib follows redirects on its own; without this, a public URL could
    # redirect the fetch to a private address after the initial check.
    def __init__(self, kind: str) -> None:
        self._kind = kind

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        verify_public_url(newurl, kind=self._kind)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_public_url(url: str, *, kind: str = "url", timeout: float) -> HTTPResponse:
    """Open ``url`` after :func:`verify_public_url`, re-checking every redirect."""
    verify_public_url(url, kind=kind)
    opener = urllib.request.build_opener(_PublicRedirectHandler(kind))
    response: HTTPResponse = opener.open(url, timeout=timeout)
    return response
