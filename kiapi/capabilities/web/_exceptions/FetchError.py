class FetchError(RuntimeError):
    """A fetch could not produce usable page content.

    Carries a machine-readable ``code`` (``fetch_failed`` / ``not_html`` /
    ``empty_content``), the HTTP ``status_code`` the API layer should surface,
    and — when the preflight probe revealed it — the upstream resource's
    ``content_type``, so the caller learns *why* (e.g. it was a ``image/png``).

    Status mapping: 502/504 = backend unreachable/timed out (``fetch_failed``);
    422 = reachable but not a usable HTML page (``not_html`` / ``empty_content``).
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        content_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.content_type = content_type
