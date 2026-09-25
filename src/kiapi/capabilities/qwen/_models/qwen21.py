"""Handler for Qwen-Image-2.1 generate/edit via mflux.

One resident model serves both operations: Qwen-Image-2.1 unifies
text-to-image and reference editing, and outputs RGBA.
"""

import gc
import time
from types import SimpleNamespace
from typing import Any

from kiapi.capabilities import attach_mflux_progress
from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec

from .._operations.store_image import store_image
from .._views.edit_params import EditParams
from .._views.generate_params import GenerateParams

FEATURES = {"text", "image"}


def _build_model(spec: ModelSpec, *, quantize: int | None) -> Any:
    from mflux.models.qwen21.reference import (  # type: ignore[import-untyped]
        QwenImage21Edit,
    )

    return QwenImage21Edit(quantize=quantize, model_path=spec.repo)


def load(spec: ModelSpec) -> SimpleNamespace:
    from .._settings import settings_manager

    quantize = settings_manager.get_settings().image_21_quantize
    return SimpleNamespace(
        model=_build_model(spec, quantize=quantize), spec=spec, quantize=quantize
    )


def warmup(payload: SimpleNamespace) -> None:
    _run(
        payload.model,
        seed=0,
        prompt="warmup",
        negative_prompt=None,
        steps=2,
        width=256,
        height=256,
        guidance=1.0,
        image_paths=[],
        reference_resolution=None,
    )


def _run(
    model: Any,
    *,
    seed: int,
    prompt: str,
    negative_prompt: str | None,
    steps: int,
    width: int,
    height: int,
    guidance: float,
    image_paths: list[str],
    reference_resolution: int | None,
) -> Any:
    attach_mflux_progress(model)
    kwargs: dict[str, Any] = {}
    if reference_resolution is not None:
        kwargs["output_resolution"] = reference_resolution
    try:
        return model.generate_image(
            seed=seed,
            prompt=prompt,
            # mflux enables true CFG only when a negative prompt is present.
            negative_prompt=(negative_prompt or "") if guidance > 1 else None,
            num_inference_steps=steps,
            width=width,
            height=height,
            guidance=guidance,
            image_paths=image_paths,
            **kwargs,
        )
    finally:
        # mflux caches every text-only prompt embedding; drop them so a
        # resident model does not grow with each distinct prompt.
        model.prompt_cache.clear()


def _generate(model: Any, params: GenerateParams, files: FileStore) -> dict[str, Any]:
    t0 = time.time()
    image = _run(
        model,
        seed=params.seed,
        prompt=params.prompt,
        negative_prompt=params.negative_prompt,
        steps=params.steps,
        width=params.width,
        height=params.height,
        guidance=params.guidance,
        image_paths=[],
        reference_resolution=None,
    )
    meta = {
        "model": params.model,
        "prompt": params.prompt,
        "params": params.model_dump(exclude={"image_path", "scheduler"}),
        "width": params.width,
        "height": params.height,
        "timings": {"total_s": round(time.time() - t0, 2)},
    }
    return store_image(
        image, fmt=params.format, quality=params.quality, files=files, meta=meta
    )


def _edit(model: Any, params: EditParams, files: FileStore) -> dict[str, Any]:
    t0 = time.time()
    image = _run(
        model,
        seed=params.seed,
        prompt=params.prompt,
        negative_prompt=params.negative_prompt,
        steps=params.steps,
        width=params.width,
        height=params.height,
        guidance=params.guidance,
        image_paths=params.image_paths,
        reference_resolution=params.reference_resolution,
    )
    meta = {
        "model": params.model,
        "prompt": params.prompt,
        "params": params.model_dump(exclude={"image_paths", "scheduler"}),
        "width": params.width,
        "height": params.height,
        "timings": {"total_s": round(time.time() - t0, 2)},
    }
    return store_image(
        image, fmt=params.format, quality=params.quality, files=files, meta=meta
    )


def run_generate(
    payload: SimpleNamespace, params: GenerateParams, files: FileStore
) -> dict[str, Any]:
    return _generate(payload.model, params, files)


def run_edit(
    payload: SimpleNamespace, params: EditParams, files: FileStore
) -> dict[str, Any]:
    return _edit(payload.model, params, files)


def run_generate_transient(
    spec: ModelSpec, params: GenerateParams, files: FileStore
) -> dict[str, Any]:
    model = _build_model(spec, quantize=params.quantize)
    try:
        return _generate(model, params, files)
    finally:
        _free(model)


def run_edit_transient(
    spec: ModelSpec, params: EditParams, files: FileStore
) -> dict[str, Any]:
    model = _build_model(spec, quantize=params.quantize)
    try:
        return _edit(model, params, files)
    finally:
        _free(model)


def _free(model: Any) -> None:
    del model
    gc.collect()
    import mlx.core as mx

    mx.clear_cache()
