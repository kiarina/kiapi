import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from kiapi.capabilities.chat._utils.read_context_window import read_context_window


def _spec(repo: Path, keys: tuple[str, ...]) -> Any:
    return SimpleNamespace(
        repo=str(repo), module=SimpleNamespace(CONTEXT_WINDOW_KEYS=keys)
    )


def test_reads_the_nested_context_window_from_a_local_config(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps(
            {"thinker_config": {"text_config": {"max_position_embeddings": 65536}}}
        )
    )

    spec = _spec(tmp_path, ("thinker_config", "text_config", "max_position_embeddings"))

    assert read_context_window(spec) == 65536


def test_returns_none_when_the_key_path_is_missing(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"text_config": {}}))

    spec = _spec(tmp_path, ("text_config", "max_position_embeddings"))

    assert read_context_window(spec) is None


def test_returns_none_when_the_config_is_not_available(tmp_path: Path) -> None:
    spec = _spec(tmp_path / "missing", ("text_config", "max_position_embeddings"))

    assert read_context_window(spec) is None
