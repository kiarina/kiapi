from .._views.relay_error import RelayError


class RelayRequestError(RuntimeError):
    """Raised when a relay request terminates with a failure notification."""

    def __init__(self, error: RelayError) -> None:
        self.error = error
        super().__init__(f"relay request failed [{error.code}]: {error.message}")
