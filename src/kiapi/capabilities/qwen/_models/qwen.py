"""Handler for Qwen Image generate/edit via mflux."""

import gc
import time
from types import SimpleNamespace
from typing import Any

from kiapi.capabilities import attach_mflux_progress
from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._views.edit_params import EditParams
from .._views.generate_params import GenerateParams

FEATURES = {"text", "image"}


def _role(spec: ModelSpec) -> str:
    return "edit" if spec.name == "edit-2509" else "generate"


def _build_generate_model(
    spec: ModelSpec,
    *,
    quantize: int | None,
    lora_paths: list[str] | None = None,
    lora_scales: list[float] | None = None,
) -> Any:
    from mflux.models.common.config import ModelConfig  # type: ignore
    from mflux.models.qwen.variants.txt2img.qwen_image import QwenImage  # type: ignore

    return QwenImage(
        quantize=quantize,
        model_path=spec.repo,
        lora_paths=lora_paths or None,
        lora_scales=lora_scales or None,
        model_config=ModelConfig.qwen_image(),
    )


def _build_edit_model(
    spec: ModelSpec,
    *,
    quantize: int | None,
    lora_paths: list[str] | None = None,
    lora_scales: list[float] | None = None,
) -> Any:
    from mflux.models.common.config import ModelConfig
    from mflux.models.qwen.variants.edit.qwen_image_edit import (  # type: ignore[import-untyped]
        QwenImageEdit,
    )

    return QwenImageEdit(
        quantize=quantize,
        model_path=spec.repo,
        lora_paths=lora_paths or None,
        lora_scales=lora_scales or None,
        model_config=ModelConfig.qwen_image_edit(),
    )


def load(spec: ModelSpec) -> SimpleNamespace:
    from .._settings import settings_manager

    settings = settings_manager.get_settings()
    role = _role(spec)
    quantize = settings.default_quantize
    model = (
        _build_edit_model(spec, quantize=quantize)
        if role == "edit"
        else _build_generate_model(spec, quantize=quantize)
    )
    return SimpleNamespace(model=model, spec=spec, role=role, quantize=quantize)


def warmup(payload: SimpleNamespace) -> None:
    if payload.role == "edit":
        return
    payload.model.generate_image(
        seed=0, prompt="warmup", num_inference_steps=1, width=256, height=256
    )


def _store_image(
    image: Any,
    *,
    fmt: str,
    quality: int,
    files: FileStore,
    meta: dict[str, Any],
) -> dict[str, Any]:
    pil = getattr(image, "image", image)
    ext = "jpg" if fmt == "jpeg" else fmt
    tmp_dir = create_work_dir("image/qwen")
    out_path = tmp_dir / f"image.{ext}"
    save_kwargs: dict[str, Any] = {}
    if fmt in ("jpeg", "webp"):
        save_kwargs["quality"] = quality
    if fmt == "jpeg":
        pil = pil.convert("RGB")
    pil.save(out_path, format=fmt.upper(), **save_kwargs)
    if not out_path.exists():
        raise RuntimeError("generation finished but no image file was produced")
    rec = files.put_path(
        out_path,
        filename=f"qwen_{int(time.time())}.{ext}",
        content_type=f"image/{fmt}",
        meta=meta,
        move=True,
    )
    return {"file_id": rec.file_id, "image_bytes": rec.size, **meta}


def _generate(model: Any, params: GenerateParams, files: FileStore) -> dict[str, Any]:
    t0 = time.time()
    attach_mflux_progress(model)
    image = model.generate_image(
        seed=params.seed,
        prompt=params.prompt,
        negative_prompt=params.negative_prompt,
        image_path=params.image_path,
        image_strength=params.image_strength,
        num_inference_steps=params.steps,
        width=params.width,
        height=params.height,
        guidance=params.guidance,
        scheduler=params.scheduler,
    )
    total_s = round(time.time() - t0, 2)
    meta = {
        "model": params.model,
        "prompt": params.prompt,
        "params": params.model_dump(exclude={"image_path"}),
        "width": params.width,
        "height": params.height,
        "timings": {"total_s": total_s},
    }
    return _store_image(
        image, fmt=params.format, quality=params.quality, files=files, meta=meta
    )


def _edit(model: Any, params: EditParams, files: FileStore) -> dict[str, Any]:
    t0 = time.time()
    attach_mflux_progress(model)
    image = model.generate_image(
        seed=params.seed,
        prompt=params.prompt,
        negative_prompt=params.negative_prompt,
        image_paths=params.image_paths,
        image_path=params.image_paths[0],
        num_inference_steps=params.steps,
        width=params.width,
        height=params.height,
        guidance=params.guidance,
        scheduler=params.scheduler,
    )
    total_s = round(time.time() - t0, 2)
    meta = {
        "model": params.model,
        "prompt": params.prompt,
        "params": params.model_dump(exclude={"image_paths"}),
        "width": params.width,
        "height": params.height,
        "timings": {"total_s": total_s},
    }
    return _store_image(
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
    spec: ModelSpec,
    params: GenerateParams,
    files: FileStore,
    *,
    lora_paths: list[str],
    lora_scales: list[float],
) -> dict[str, Any]:
    model = _build_generate_model(
        spec, quantize=params.quantize, lora_paths=lora_paths, lora_scales=lora_scales
    )
    try:
        return _generate(model, params, files)
    finally:
        _free(model)


def run_edit_transient(
    spec: ModelSpec,
    params: EditParams,
    files: FileStore,
    *,
    lora_paths: list[str],
    lora_scales: list[float],
) -> dict[str, Any]:
    model = _build_edit_model(
        spec, quantize=params.quantize, lora_paths=lora_paths, lora_scales=lora_scales
    )
    try:
        return _edit(model, params, files)
    finally:
        _free(model)


def _free(model: Any) -> None:
    del model
    gc.collect()
    import mlx.core as mx

    mx.clear_cache()
