"""FLUX.2 LoRA finetune service entry (always-async worker-thread thunk)."""

import shutil
import zipfile
from pathlib import Path

from kiapi.capabilities import CapabilityError, get_file_path
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry
from kiapi.core.workdir import create_work_dir

from .._settings import settings_manager
from .._views.train_request import TrainRequest
from .resolve_train_params import resolve_train_params

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def handle_train(ctx: AppContext, req: TrainRequest) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("flux2", req.model or settings.train_default_model)
    ctx.ensure_model_ready(spec)
    if "base" not in spec.name:
        raise CapabilityError(
            "Flux2 training requires a base variant: klein-base-4b or klein-base-9b"
        )

    dataset_path = get_file_path(ctx.file_store, req.dataset, kind="dataset")

    workdir = create_work_dir("train/flux2")
    try:
        data_dir = _extract_dataset(dataset_path, workdir / "data")
        n_images = _validate_dataset(data_dir, training_mode=req.training_mode)
        params = resolve_train_params(settings, req, variant=spec.name)
        ctx.memory_manager.reserve(settings.train_reserve_gb)
        result = spec.module.train(spec, params, ctx.file_store, str(data_dir))
        result["num_images"] = n_images
        return result, [result["adapter_file_id"]]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _extract_dataset(zip_path: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise CapabilityError(f"unsafe path in dataset zip: {member!r}")
        zf.extractall(dest)

    def _has_images(d: Path) -> bool:
        return any(p.suffix.lower() in _IMAGE_EXTS for p in d.iterdir() if p.is_file())

    if _has_images(dest):
        return dest
    subdirs = [p for p in dest.iterdir() if p.is_dir()]
    if len(subdirs) == 1 and _has_images(subdirs[0]):
        return subdirs[0]
    raise CapabilityError(
        "dataset zip must contain images at the top level or in a single subfolder"
    )


def _validate_dataset(data_dir: Path, *, training_mode: str) -> int:
    images = [
        p for p in data_dir.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    ]
    if not images:
        raise CapabilityError("dataset has no images")
    out_images = [p for p in images if p.stem.endswith("_out")]
    if training_mode == "edit":
        if not out_images:
            raise CapabilityError(
                "edit training dataset must contain *_in / *_out image pairs"
            )
        count = 0
        for out_path in out_images:
            base = out_path.stem[:-4]
            if not any((data_dir / f"{base}_in{ext}").exists() for ext in _IMAGE_EXTS):
                raise CapabilityError(
                    f"missing input image for {out_path.name}: expected {base}_in.*"
                )
            if not (data_dir / f"{base}_in.txt").exists():
                raise CapabilityError(
                    f"missing prompt file for {base}_in.*: expected {base}_in.txt"
                )
            count += 1
        return count

    if out_images:
        raise CapabilityError(
            "text training dataset must not use *_in / *_out edit pairs"
        )
    missing = [
        p.name
        for p in images
        if not p.stem.startswith("preview")
        and not (data_dir / f"{p.stem}.txt").exists()
    ]
    if missing:
        raise CapabilityError(f"images missing a same-stem .txt caption: {missing}")
    return len([p for p in images if not p.stem.startswith("preview")])
