"""Load an mlx-vlm model + processor. Shared by every chat model's ``load()``."""

from types import SimpleNamespace

from kiapi.core.model import ModelSpec

from .read_context_window import read_context_window


def load_mlx_vlm(spec: ModelSpec) -> SimpleNamespace:
    from mlx_vlm import load

    model, processor = load(spec.repo)
    return SimpleNamespace(
        model=model,
        processor=processor,
        context_window=read_context_window(spec),
    )
