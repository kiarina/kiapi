"""Build (or reuse) a Qwen4-Exp checkpoint view whose PLE table is memory-mapped.

Qwen3.8-Flash-Next carries a ~32 GB n-gram (PLE) embedding table of which each
token reads a few rows. mlx-vlm serves it from a memory map when
``text_config.ple_storage`` names a ``ple-store.json`` manifest; otherwise it
loads the whole table as MLX parameters. The mlx-community conversion ships no
manifest, so this builds a view next to the snapshot instead of editing it:

  - non-PLE weight files and the small tokenizer/processor files are symlinked,
  - the weight index drops the PLE tensors,
  - ``config.json`` gains ``text_config.ple_storage``,
  - ``ple-store.json`` indexes the PLE byte ranges inside the snapshot files.

No weight payload is copied. The view is rebuilt when the snapshot path changes
(a new revision) and must be rebuilt if the snapshot is deleted.
"""

import json
import os
import shutil
from pathlib import Path

MARKER = "EXTERNAL_PLE.json"
FORMAT = "kiapi_external_ple_v1"


def prepare_external_ple_view(snapshot: Path, view: Path) -> Path:
    snapshot = snapshot.resolve()
    if _is_current(snapshot, view):
        return view

    from mlx_vlm.models.qwen4_exp.ple_storage import (
        PLE_MARKER,
        build_quantized_ple_manifest,
    )

    staging = view.with_name(view.name + ".tmp")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)

    manifest = build_quantized_ple_manifest(snapshot, staging / "ple-store.json")
    manifest["source_root"] = str(snapshot)
    _write_json(staging / "ple-store.json", manifest)

    index = json.loads((snapshot / "model.safetensors.index.json").read_text())
    weight_map = {
        key: file for key, file in index["weight_map"].items() if PLE_MARKER not in key
    }
    _write_json(
        staging / "model.safetensors.index.json", {**index, "weight_map": weight_map}
    )

    config = json.loads((snapshot / "config.json").read_text())
    config["text_config"]["ple_storage"] = {
        "manifest": "ple-store.json",
        "cache_rows": 0,
    }
    if isinstance(config.get("quantization"), dict):
        config["quantization"] = {
            key: value
            for key, value in config["quantization"].items()
            if PLE_MARKER not in key
        }
    _write_json(staging / "config.json", config)

    linked = set(weight_map.values())
    for source in snapshot.iterdir():
        if source.name in {"config.json", "model.safetensors.index.json"}:
            continue
        if source.suffix == ".safetensors" and source.name not in linked:
            continue  # PLE-only shard, read through the manifest
        os.symlink(source, staging / source.name)

    _write_json(staging / MARKER, {"format": FORMAT, "source": str(snapshot)})
    shutil.rmtree(view, ignore_errors=True)
    staging.rename(view)
    return view


def _is_current(snapshot: Path, view: Path) -> bool:
    try:
        marker = json.loads((view / MARKER).read_text())
    except (OSError, ValueError):
        return False
    return (
        marker.get("format") == FORMAT
        and marker.get("source") == str(snapshot)
        and (view / "ple-store.json").is_file()
    )


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")
