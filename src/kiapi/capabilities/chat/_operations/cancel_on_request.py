"""Stop a chat generation iterator when its job requests cancellation."""

from collections.abc import Callable, Iterator
from typing import Any

from kiapi.core.job import JobCanceledError


def cancel_on_request(
    chunks: Iterator[Any],
    cancel_requested: Callable[[], bool] | None,
    on_cancel: Callable[[], None] | None = None,
) -> Iterator[Any]:
    if cancel_requested is None:
        yield from chunks
        return

    try:
        while True:
            if cancel_requested():
                raise JobCanceledError
            try:
                chunk = next(chunks)
            except StopIteration:
                return
            if cancel_requested():
                raise JobCanceledError
            yield chunk
    except JobCanceledError:
        if on_cancel is not None:
            on_cancel()
        raise
    finally:
        close = getattr(chunks, "close", None)
        if callable(close):
            close()
        _clear_mlx_cache()


def _clear_mlx_cache() -> None:
    try:
        import mlx.core as mx

        mx.clear_cache()
    except ImportError:
        pass
