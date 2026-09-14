"""Handler for Depth Pro image → depth map via mflux."""

import gc
import time
from types import SimpleNamespace
from typing import Any

import numpy as np
from PIL import Image

from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._views.estimate_params import EstimateParams

FEATURES = {"image", "depth"}


def build_model(*, quantize: int | None) -> Any:
    from mflux.models.depth_pro.model.depth_pro import DepthPro  # type: ignore

    return DepthPro(quantize=quantize)


def load(spec: ModelSpec) -> SimpleNamespace:
    from .._settings import settings_manager

    quantize = settings_manager.get_settings().default_quantize
    model = build_model(quantize=quantize)
    return SimpleNamespace(model=model, spec=spec, quantize=quantize)


def _store_depth_image(
    result: Any,
    *,
    files: FileStore,
    meta: dict[str, Any],
) -> dict[str, Any]:
    pil = result.depth_image
    tmp_dir = create_work_dir("image/depthpro")
    out_path = tmp_dir / "depth.png"
    pil.save(out_path, format="PNG")
    if not out_path.exists():
        raise RuntimeError("depth estimation finished but no depth image was produced")
    rec = files.put_path(
        out_path,
        filename=f"depthpro_{int(time.time())}.png",
        content_type="image/png",
        meta=meta | {"kind": "depth_image"},
        move=True,
    )
    return {"depth_image_file_id": rec.file_id, "depth_image_bytes": rec.size}


def _store_depth_data(
    result: Any,
    *,
    files: FileStore,
    meta: dict[str, Any],
) -> dict[str, Any]:
    tmp_dir = create_work_dir("image/depthpro")
    out_path = tmp_dir / "depth.npz"
    np.savez_compressed(
        out_path,
        depth=np.asarray(result.depth_array),
        min_depth=float(result.min_depth),
        max_depth=float(result.max_depth),
    )
    if not out_path.exists():
        raise RuntimeError(
            "depth estimation finished but no depth data file was produced"
        )
    rec = files.put_path(
        out_path,
        filename=f"depthpro_{int(time.time())}.npz",
        content_type="application/octet-stream",
        meta=meta | {"kind": "depth_data", "format": "npz"},
        move=True,
    )
    return {"depth_data_file_id": rec.file_id, "depth_data_bytes": rec.size}


def _estimate(
    model: Any,
    spec: ModelSpec,
    params: EstimateParams,
    files: FileStore,
) -> dict[str, Any]:
    with Image.open(params.image_path) as src:
        input_size = src.size
        input_mode = src.mode

    t0 = time.time()
    result = model.create_depth_map(params.image_path)
    total_s = round(time.time() - t0, 2)

    depth_array = np.asarray(result.depth_array)
    meta = {
        "model": spec.name,
        "params": params.model_dump(exclude={"image_path"}),
        "input_width": input_size[0],
        "input_height": input_size[1],
        "input_mode": input_mode,
        "width": result.depth_image.width,
        "height": result.depth_image.height,
        "mode": result.depth_image.mode,
        "array_shape": list(depth_array.shape),
        "min_depth": round(float(result.min_depth), 6),
        "max_depth": round(float(result.max_depth), 6),
        "timings": {"total_s": total_s},
    }

    stored = _store_depth_image(result, files=files, meta=meta)
    if params.include_depth_data:
        stored |= _store_depth_data(result, files=files, meta=meta)
    else:
        stored["depth_data_file_id"] = None
        stored["depth_data_bytes"] = None
    return {**stored, **meta}


def run(
    payload: SimpleNamespace,
    params: EstimateParams,
    files: FileStore,
) -> dict[str, Any]:
    return _estimate(payload.model, payload.spec, params, files)


def run_transient(
    spec: ModelSpec,
    params: EstimateParams,
    files: FileStore,
) -> dict[str, Any]:
    model = build_model(quantize=params.quantize)
    try:
        return _estimate(model, spec, params, files)
    finally:
        del model
        gc.collect()
        import mlx.core as mx

        mx.clear_cache()
