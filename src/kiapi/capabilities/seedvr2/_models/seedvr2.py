"""Handler for SeedVR2 image upscale via mflux."""

import gc
import time
from types import SimpleNamespace
from typing import Any

from PIL import Image

from kiapi.capabilities import attach_mflux_progress
from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._views.upscale_params import UpscaleParams

FEATURES = {"image", "upscale"}


def _variant(spec: ModelSpec) -> str:
    return spec.name


def _repo_base(spec: ModelSpec) -> str:
    base, _sep, _variant_name = spec.repo.partition("#")
    return base


def _model_config(spec: ModelSpec) -> Any:
    from mflux.models.common.config import ModelConfig  # type: ignore

    return (
        ModelConfig.seedvr2_7b() if _variant(spec) == "7b" else ModelConfig.seedvr2_3b()
    )


def _resolution(value: int | str) -> int | Any:
    if isinstance(value, int):
        return value
    if value.endswith("x"):
        from mflux.utils.scale_factor import ScaleFactor  # type: ignore

        return ScaleFactor.parse(value)
    return int(value)


def build_model(spec: ModelSpec, *, quantize: int | None) -> Any:
    from mflux.models.seedvr2 import SeedVR2  # type: ignore

    model_config = _model_config(spec)
    return SeedVR2(
        quantize=quantize, model_path=_repo_base(spec), model_config=model_config
    )


def load(spec: ModelSpec) -> SimpleNamespace:
    from .._settings import settings_manager

    quantize = settings_manager.get_settings().default_quantize
    model = build_model(spec, quantize=quantize)
    return SimpleNamespace(model=model, spec=spec, quantize=quantize)


def _store_image(
    generated: Any,
    *,
    params: UpscaleParams,
    files: FileStore,
    meta: dict[str, Any],
) -> dict[str, Any]:
    pil = generated.image if hasattr(generated, "image") else generated
    fmt = params.format
    ext = "jpg" if fmt == "jpeg" else fmt
    tmp_dir = create_work_dir("image/seedvr2")
    out_path = tmp_dir / f"image.{ext}"
    save_kwargs: dict[str, Any] = {}
    if fmt in ("jpeg", "webp"):
        save_kwargs["quality"] = params.quality
    if fmt == "jpeg":
        pil = pil.convert("RGB")
    pil.save(out_path, format=fmt.upper(), **save_kwargs)
    if not out_path.exists():
        raise RuntimeError("upscale finished but no image file was produced")
    rec = files.put_path(
        out_path,
        filename=f"seedvr2_{int(time.time())}.{ext}",
        content_type=f"image/{fmt}",
        meta=meta,
        move=True,
    )
    return {"file_id": rec.file_id, "image_bytes": rec.size, **meta}


def _upscale(model: Any, params: UpscaleParams, files: FileStore) -> dict[str, Any]:
    resolution = _resolution(params.resolution)
    with Image.open(params.image_path) as src:
        input_size = src.size

    t0 = time.time()
    attach_mflux_progress(model)
    image = model.generate_image(
        seed=params.seed,
        image_path=params.image_path,
        resolution=resolution,
        softness=params.softness,
    )
    total_s = round(time.time() - t0, 2)

    pil = image.image if hasattr(image, "image") else image
    output_size = pil.size
    meta = {
        "model": params.model,
        "params": params.model_dump(exclude={"image_path"}),
        "input_width": input_size[0],
        "input_height": input_size[1],
        "width": output_size[0],
        "height": output_size[1],
        "timings": {"total_s": total_s},
    }
    return _store_image(image, params=params, files=files, meta=meta)


def run(
    payload: SimpleNamespace, params: UpscaleParams, files: FileStore
) -> dict[str, Any]:
    return _upscale(payload.model, params, files)


def run_transient(
    spec: ModelSpec, params: UpscaleParams, files: FileStore
) -> dict[str, Any]:
    model = build_model(spec, quantize=params.quantize)
    try:
        return _upscale(model, params, files)
    finally:
        del model
        gc.collect()
        import mlx.core as mx

        mx.clear_cache()
