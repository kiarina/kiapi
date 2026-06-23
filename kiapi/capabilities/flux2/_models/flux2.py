"""Handler for FLUX.2 Klein (generate/edit/train) via mflux."""

import gc
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from kiapi.capabilities import attach_mflux_progress
from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._operations.split_repo import split_repo
from .._views.edit_params import EditParams
from .._views.generate_params import GenerateParams
from .._views.train_params import TrainParams

FEATURES = {"text", "image"}


def _model_config(model_name: str) -> Any:
    from mflux.models.common.config import ModelConfig  # type: ignore

    return ModelConfig.from_name(model_name=model_name)


def _build_generate_model(
    spec: ModelSpec,
    *,
    quantize: int | None,
    lora_paths: list[str] | None = None,
    lora_scales: list[float] | None = None,
) -> Any:
    from mflux.models.flux2.variants import Flux2Klein  # type: ignore

    model_name, _role = split_repo(spec.repo)
    return Flux2Klein(
        model_config=_model_config(model_name),
        quantize=quantize,
        lora_paths=lora_paths or None,
        lora_scales=lora_scales or None,
    )


def _build_edit_model(
    spec: ModelSpec,
    *,
    quantize: int | None,
    lora_paths: list[str] | None = None,
    lora_scales: list[float] | None = None,
) -> Any:
    from mflux.models.flux2.variants import Flux2KleinEdit

    model_name, _role = split_repo(spec.repo)
    return Flux2KleinEdit(
        model_config=_model_config(model_name),
        quantize=quantize,
        lora_paths=lora_paths or None,
        lora_scales=lora_scales or None,
    )


def load(spec: ModelSpec) -> SimpleNamespace:
    from .._settings import settings_manager

    settings = settings_manager.get_settings()
    model_name, role = split_repo(spec.repo)
    quantize = settings.default_quantize.get(spec.name)
    model = (
        _build_edit_model(spec, quantize=quantize)
        if role == "edit"
        else _build_generate_model(spec, quantize=quantize)
    )
    return SimpleNamespace(
        model=model, spec=spec, model_name=model_name, role=role, quantize=quantize
    )


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
    tmp_dir = create_work_dir("image/flux2")
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
        filename=f"flux2_{int(time.time())}.{ext}",
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
        image_path=params.init_image_path,
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
        "params": params.model_dump(exclude={"init_image_path"}),
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
        image_paths=params.image_paths,
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


_BLOCK_RANGE = {"start": 0, "end": 2}
_SINGLE_BLOCK_RANGE = {"start": 0, "end": 6}


def _default_lora_targets(rank: int, include_ff: bool) -> list[dict[str, Any]]:
    targets = [
        {
            "module_path": f"transformer_blocks.{{block}}.attn.{name}",
            "blocks": dict(_BLOCK_RANGE),
            "rank": rank,
        }
        for name in (
            "to_q",
            "to_k",
            "to_v",
            "to_out",
            "add_q_proj",
            "add_k_proj",
            "add_v_proj",
            "to_add_out",
        )
    ]
    if include_ff:
        targets += [
            {
                "module_path": f"transformer_blocks.{{block}}.{name}",
                "blocks": dict(_BLOCK_RANGE),
                "rank": rank,
            }
            for name in (
                "ff.linear_in",
                "ff.linear_out",
                "ff_context.linear_in",
                "ff_context.linear_out",
            )
        ]
    targets += [
        {
            "module_path": "single_transformer_blocks.{block}.attn.to_qkv_mlp_proj",
            "blocks": dict(_SINGLE_BLOCK_RANGE),
            "rank": rank,
        },
        {
            "module_path": "single_transformer_blocks.{block}.attn.to_out",
            "blocks": dict(_SINGLE_BLOCK_RANGE),
            "rank": rank,
        },
    ]
    return targets


def _train_model_name(spec: ModelSpec, params: TrainParams) -> str:
    base, _role = split_repo(spec.repo)
    return f"{base}-edit" if params.training_mode == "edit" else base


def _build_train_config(
    spec: ModelSpec,
    params: TrainParams,
    data_dirname: str,
    out_dir: Path,
) -> dict[str, Any]:
    lora_layers = params.lora_layers or {
        "targets": _default_lora_targets(params.lora_rank, params.lora_include_ff)
    }

    return {
        "model": _train_model_name(spec, params),
        "data": data_dirname,
        "seed": params.seed,
        "steps": params.steps,
        "guidance": params.guidance,
        "quantize": params.quantize,
        "max_resolution": params.max_resolution,
        "low_ram": params.low_ram,
        "training_loop": {
            "num_epochs": params.num_epochs,
            "batch_size": params.batch_size,
            "timestep_low": params.timestep_low,
            "timestep_high": params.timestep_high,
        },
        "optimizer": {"name": "AdamW", "learning_rate": params.learning_rate},
        "checkpoint": {
            "save_frequency": params.save_frequency,
            "output_path": str(out_dir),
        },
        "lora_layers": lora_layers,
    }


def train(
    spec: ModelSpec,
    params: TrainParams,
    files: FileStore,
    dataset_dir: str,
) -> dict[str, Any]:
    import zipfile

    from mflux.models.common.training.runner import TrainingRunner  # type: ignore
    from mflux.utils.exceptions import StopTrainingException  # type: ignore

    workdir = Path(dataset_dir).parent
    out_dir = workdir / "out"
    config = _build_train_config(spec, params, Path(dataset_dir).name, out_dir)
    config_path = workdir / "train.json"
    config_path.write_text(json.dumps(config, indent=2))

    t0 = time.time()
    try:
        _adapter, training_spec = TrainingRunner.train(
            config_path=str(config_path), resume_path=None
        )
    except StopTrainingException:
        from mflux.models.common.training.state.training_spec import (  # type: ignore[import-untyped]
            TrainingSpec,
        )

        training_spec = TrainingSpec.resolve(
            config_path=str(config_path), resume_path=None
        )
    total_s = round(time.time() - t0, 2)

    ckpt_dir = Path(training_spec.checkpoint.output_path) / "checkpoints"
    zips = sorted(ckpt_dir.glob("*_checkpoint.zip"))
    if not zips:
        raise RuntimeError(
            f"training finished but no checkpoint was produced in {ckpt_dir}"
        )
    latest = zips[-1]

    adapter_bytes = None
    with zipfile.ZipFile(latest) as zf:
        for name in zf.namelist():
            if name.endswith("_adapter.safetensors"):
                adapter_bytes = zf.read(name)
                break
    if adapter_bytes is None:
        raise RuntimeError(f"no *_adapter.safetensors inside {latest.name}")

    meta = {
        "model": spec.name,
        "kind": "lora_adapter",
        "training_mode": params.training_mode,
        "config": {
            k: config[k]
            for k in (
                "model",
                "seed",
                "steps",
                "guidance",
                "quantize",
                "max_resolution",
                "low_ram",
                "training_loop",
                "optimizer",
            )
        },
        "lora_targets": len(config["lora_layers"]["targets"]),
        "checkpoint": latest.name,
        "timings": {"total_s": total_s},
    }
    rec = files.put_bytes(
        adapter_bytes,
        filename=f"flux2_lora_{spec.name}_{int(time.time())}.safetensors",
        content_type="application/octet-stream",
        meta=meta,
    )
    return {"adapter_file_id": rec.file_id, "adapter_bytes": rec.size, **meta}
