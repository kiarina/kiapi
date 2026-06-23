"""Unit tests for AceStepEngine's protocol loop (no subprocess, CPU-only).

A fake Popen-like object feeds canned ``@@KIAPI@@`` lines through ``stdout`` and
captures requests written to ``stdin``, so we can drive ``generate`` without the
ace-step venv or any model.
"""

import json

import pytest

from kiapi.capabilities.acestep._exceptions.ace_step_engine_error import (
    AceStepEngineError,
)
from kiapi.capabilities.acestep._services.ace_step_engine import SENTINEL, AceStepEngine


class _FakeStdin:
    def __init__(self) -> None:
        self.written: list[str] = []

    def write(self, s: str) -> None:
        self.written.append(s)

    def flush(self) -> None:
        pass


class _FakeProc:
    """Minimal subprocess.Popen stand-in: stdout yields pre-seeded lines."""

    def __init__(self, lines: list[str]) -> None:
        self.stdin = _FakeStdin()
        self.stdout = iter([line + "\n" for line in lines])
        self.returncode = 0
        self._alive = True

    def poll(self) -> int | None:
        return None if self._alive else self.returncode


def _proto(obj: dict) -> str:
    return SENTINEL + json.dumps(obj)


def test_generate_forwards_progress_then_returns_path() -> None:
    proc = _FakeProc(
        [
            "some ace-step log noise on fd1",  # skipped (no sentinel)
            _proto(
                {"id": "1", "event": "progress", "fraction": 0.1, "label": "Phase 1"}
            ),
            _proto(
                {"id": "1", "event": "progress", "fraction": 0.52, "label": "Diffusion"}
            ),
            _proto({"id": "1", "ok": True, "path": "/tmp/out.wav"}),
        ]
    )
    engine = AceStepEngine(proc)  # type: ignore[arg-type]

    seen: list[tuple[float, str | None]] = []
    path = engine.generate(
        "text2music",
        {"prompt": "x"},
        "/tmp/save",
        timeout_s=10.0,
        on_progress=lambda f, label: seen.append((f, label)),
    )

    assert path == "/tmp/out.wav"
    assert seen == [(0.1, "Phase 1"), (0.52, "Diffusion")]
    # the request was actually sent with the matching id
    sent = json.loads(proc.stdin.written[0])
    assert sent["id"] == "1"
    assert sent["task"] == "text2music"


def test_generate_without_callback_ignores_progress() -> None:
    proc = _FakeProc(
        [
            _proto({"id": "1", "event": "progress", "fraction": 0.5}),
            _proto({"id": "1", "ok": True, "path": "/tmp/out.wav"}),
        ]
    )
    engine = AceStepEngine(proc)  # type: ignore[arg-type]

    assert engine.generate("cover", {}, "/tmp", timeout_s=10.0) == "/tmp/out.wav"


def test_generate_raises_on_worker_error_reply() -> None:
    proc = _FakeProc(
        [
            _proto({"id": "1", "event": "progress", "fraction": 0.1}),
            _proto({"id": "1", "ok": False, "error": "boom"}),
        ]
    )
    engine = AceStepEngine(proc)  # type: ignore[arg-type]

    with pytest.raises(AceStepEngineError, match="boom"):
        engine.generate("text2music", {}, "/tmp", timeout_s=10.0)


def test_progress_for_other_id_is_not_forwarded() -> None:
    proc = _FakeProc(
        [
            _proto({"id": "99", "event": "progress", "fraction": 0.3}),  # stale id
            _proto({"id": "1", "ok": True, "path": "/tmp/out.wav"}),
        ]
    )
    engine = AceStepEngine(proc)  # type: ignore[arg-type]

    seen: list[tuple[float, str | None]] = []
    engine.generate(
        "text2music",
        {},
        "/tmp",
        timeout_s=10.0,
        on_progress=lambda f, label: seen.append((f, label)),
    )

    assert seen == []
