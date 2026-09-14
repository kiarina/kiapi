"""Handler for Ideogram 4 FP8 txt2img via mflux."""

import gc
import time
from types import SimpleNamespace
from typing import Any

from kiapi.capabilities import attach_mflux_progress
from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._views.generate_params import GenerateParams

FEATURES = {"text"}

_SAFETY_FILTER_NOTE = (
    "Ideogram 4 may return an 'Image blocked by safety filter' image; "
    "kiapi stores the returned image as-is."
)


def build_model(spec: ModelSpec, *, quantize: int | None) -> Any:
    from mflux.models.common.config import ModelConfig  # type: ignore
    from mflux.models.ideogram4 import Ideogram4  # type: ignore

    return Ideogram4(
        quantize=quantize,
        model_path=spec.repo,
        model_config=ModelConfig.ideogram4_fp8(),
    )


def load(spec: ModelSpec) -> SimpleNamespace:
    from .._settings import settings_manager

    quantize = settings_manager.get_settings().default_quantize
    model = build_model(spec, quantize=quantize)
    return SimpleNamespace(model=model, spec=spec, quantize=quantize)


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
    tmp_dir = create_work_dir("image/ideogram4")
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
        filename=f"ideogram4_{int(time.time())}.{ext}",
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
        width=params.width,
        height=params.height,
        preset=params.preset,
        strict_caption_validation=params.strict_caption_validation,
        warn_on_caption_issues=params.warn_on_caption_issues,
    )
    total_s = round(time.time() - t0, 2)
    meta = {
        "model": params.model,
        "prompt": params.prompt,
        "params": params.model_dump(),
        "width": params.width,
        "height": params.height,
        "safety_filter_note": _SAFETY_FILTER_NOTE,
        "timings": {"total_s": total_s},
    }
    return _store_image(
        image, fmt=params.format, quality=params.quality, files=files, meta=meta
    )


def run_generate(
    payload: SimpleNamespace, params: GenerateParams, files: FileStore
) -> dict[str, Any]:
    return _generate(payload.model, params, files)


def run_generate_transient(
    spec: ModelSpec, params: GenerateParams, files: FileStore
) -> dict[str, Any]:
    model = build_model(spec, quantize=params.quantize)
    try:
        return _generate(model, params, files)
    finally:
        _free(model)


def _free(model: Any) -> None:
    del model
    gc.collect()
    import mlx.core as mx

    mx.clear_cache()
