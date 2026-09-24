"""Load an mlx-vlm model + processor. Shared by every chat model's ``load()``."""

from pathlib import Path
from types import SimpleNamespace

from kiapi.core.model import ModelSpec

from .read_context_window import read_context_window


def load_mlx_vlm(spec: ModelSpec, path: Path | None = None) -> SimpleNamespace:
    from mlx_vlm import load

    model, processor = load(str(path) if path is not None else spec.repo)
    return SimpleNamespace(
        model=model,
        processor=processor,
        context_window=read_context_window(spec),
    )
