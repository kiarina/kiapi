from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from kiapi.capabilities.chat._models import qwen3_5, qwen4_exp


def test_load_uses_external_ple_view(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[Any] = []
    payload = SimpleNamespace()
    monkeypatch.setattr(
        qwen4_exp, "raise_open_file_limit", lambda: calls.append("nofile")
    )
    monkeypatch.setattr(
        "huggingface_hub.snapshot_download",
        lambda repo, local_files_only: str(tmp_path / "snapshot"),
    )

    def prepare(snapshot: Path, view: Path) -> Path:
        calls.append((snapshot, view.name))
        return tmp_path / "view"

    def load_mlx_vlm(spec: Any, path: Path) -> SimpleNamespace:
        calls.append(path)
        return payload

    monkeypatch.setattr(qwen4_exp, "prepare_external_ple_view", prepare)
    monkeypatch.setattr(qwen4_exp, "load_mlx_vlm", load_mlx_vlm)
    monkeypatch.setattr(qwen4_exp, "initialize_apc", lambda p: calls.append("apc"))

    spec = SimpleNamespace(repo="mlx-community/Qwen3.8-Flash-Next-4bit")
    loaded = qwen4_exp.load(cast(Any, spec))

    assert loaded is payload
    assert calls == [
        "nofile",
        (tmp_path / "snapshot", "mlx-community--Qwen3.8-Flash-Next-4bit"),
        tmp_path / "view",
        "apc",
    ]


def test_generation_is_shared_with_qwen3_5() -> None:
    assert qwen4_exp.run is qwen3_5.run
    assert qwen4_exp.release is qwen3_5.release
    assert qwen4_exp.FEATURES == qwen3_5.FEATURES
