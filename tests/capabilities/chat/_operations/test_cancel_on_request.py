from collections.abc import Iterator

import pytest

from kiapi.capabilities.chat._operations import cancel_on_request as operation
from kiapi.core.job import JobCanceledError


class _Chunks:
    def __init__(self) -> None:
        self.values = iter(["a", "b"])
        self.closed = False

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        return next(self.values)

    def close(self) -> None:
        self.closed = True


def test_stops_and_closes_generator_after_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = _Chunks()
    canceled = False
    cleared = False
    canceled_cleanup = False

    def clear() -> None:
        nonlocal cleared
        cleared = True

    def on_cancel() -> None:
        nonlocal canceled_cleanup
        canceled_cleanup = True

    monkeypatch.setattr(operation, "_clear_mlx_cache", clear)
    wrapped = operation.cancel_on_request(chunks, lambda: canceled, on_cancel)

    assert next(wrapped) == "a"
    canceled = True
    with pytest.raises(JobCanceledError):
        next(wrapped)

    assert chunks.closed
    assert cleared
    assert canceled_cleanup


def test_passthrough_without_cancel_callback() -> None:
    chunks = iter(["a", "b"])

    assert list(operation.cancel_on_request(chunks, None)) == ["a", "b"]
