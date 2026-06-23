class SearchBackendError(RuntimeError):
    """The SearXNG backend was unreachable, timed out, or returned an error.

    Carries the HTTP ``status_code`` the API layer should surface (502 for an
    unreachable/erroring backend, 504 for a timeout). This is a backend fault,
    not a client mistake — distinct from request validation (422).
    """

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
