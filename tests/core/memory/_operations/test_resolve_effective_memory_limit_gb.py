from types import SimpleNamespace
from typing import Any

import pytest

from kiapi.core.memory import MemorySettings
from kiapi.core.memory._operations import resolve_effective_memory_limit_gb as subject

_GB = 1024**3


def test_resolve_effective_memory_limit_uses_configured_value() -> None:
    settings = MemorySettings(memory_limit_gb=42.0)

    assert subject.resolve_effective_memory_limit_gb(settings) == 42.0


def test_resolve_effective_memory_limit_uses_80_percent_of_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=64 * _GB),
    )
    settings = MemorySettings(memory_limit_gb=None)

    assert subject.resolve_effective_memory_limit_gb(settings) == pytest.approx(51.2)


def test_log_memory_limit_warns_when_available_is_lower(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from kiapi.core.memory._operations import log_memory_limit as log_subject

    def virtual_memory() -> Any:
        return SimpleNamespace(total=64 * _GB, available=16 * _GB)

    monkeypatch.setattr(log_subject.psutil, "virtual_memory", virtual_memory)

    log_subject.log_memory_limit(MemorySettings(memory_limit_gb=None), 51.2)

    assert "exceeds currently available memory" in caplog.text
