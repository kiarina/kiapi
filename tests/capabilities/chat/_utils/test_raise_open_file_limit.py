import resource

import pytest

from kiapi.capabilities.chat._utils import raise_open_file_limit as module


def _limits(
    monkeypatch: pytest.MonkeyPatch, soft: int, hard: int
) -> list[tuple[int, int]]:
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(module.resource, "getrlimit", lambda _kind: (soft, hard))
    monkeypatch.setattr(
        module.resource, "setrlimit", lambda _kind, value: calls.append(value)
    )
    return calls


def test_raises_soft_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _limits(monkeypatch, 256, resource.RLIM_INFINITY)
    module.raise_open_file_limit()
    assert calls == [(65536, resource.RLIM_INFINITY)]


def test_caps_at_hard_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _limits(monkeypatch, 256, 10240)
    module.raise_open_file_limit()
    assert calls == [(10240, 10240)]


def test_keeps_higher_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _limits(monkeypatch, 100000, resource.RLIM_INFINITY)
    module.raise_open_file_limit()
    assert calls == []
