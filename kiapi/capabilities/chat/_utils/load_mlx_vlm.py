"""Load an mlx-vlm model + processor. Shared by every chat model's ``load()``."""

from types import SimpleNamespace

from kiapi.core.model import ModelSpec


def load_mlx_vlm(spec: ModelSpec) -> SimpleNamespace:
    from mlx_vlm import load  # type: ignore

    model, processor = load(spec.repo)
    return SimpleNamespace(model=model, processor=processor)
