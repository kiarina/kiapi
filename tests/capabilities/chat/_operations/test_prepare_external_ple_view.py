import json
import struct
from pathlib import Path

from kiapi.capabilities.chat._operations.prepare_external_ple_view import (
    prepare_external_ple_view,
)

PLE = "language_model.model.ple.ple_embedding.ngram_embedding.shards"


def _write_safetensors(
    path: Path, tensors: dict[str, tuple[str, list[int], int]]
) -> None:
    header: dict[str, object] = {}
    offset = 0
    for name, (dtype, shape, itemsize) in tensors.items():
        size = itemsize
        for dim in shape:
            size *= dim
        header[name] = {
            "dtype": dtype,
            "shape": shape,
            "data_offsets": [offset, offset + size],
        }
        offset += size
    raw = json.dumps(header).encode()
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + b"\0" * offset)


def _checkpoint(root: Path) -> Path:
    root.mkdir()
    rows, words, groups = 4, 20, 5  # row width 160, Q4 group 32
    ple: dict[str, tuple[str, list[int], int]] = {}
    for shard in range(2):
        ple[f"{PLE}.{shard}.weight"] = ("U32", [rows, words], 4)
        ple[f"{PLE}.{shard}.scales"] = ("BF16", [rows, groups], 2)
        ple[f"{PLE}.{shard}.biases"] = ("BF16", [rows, groups], 2)
    _write_safetensors(root / "model-00001-of-00002.safetensors", ple)
    _write_safetensors(
        root / "model-00002-of-00002.safetensors",
        {"language_model.model.norm.weight": ("BF16", [8], 2)},
    )
    weight_map = dict.fromkeys(ple, "model-00001-of-00002.safetensors")
    weight_map["language_model.model.norm.weight"] = "model-00002-of-00002.safetensors"
    (root / "model.safetensors.index.json").write_text(
        json.dumps({"metadata": {}, "weight_map": weight_map})
    )
    (root / "config.json").write_text(
        json.dumps(
            {
                "model_type": "qwen4_exp",
                "text_config": {"max_position_embeddings": 262144},
                "quantization": {"bits": 4, "group_size": 32, "mode": "affine"},
            }
        )
    )
    (root / "tokenizer.json").write_text("{}")
    return root


def test_builds_view_without_ple_parameters(tmp_path: Path) -> None:
    snapshot = _checkpoint(tmp_path / "snapshot")

    view = prepare_external_ple_view(snapshot, tmp_path / "view")

    config = json.loads((view / "config.json").read_text())
    assert config["text_config"]["ple_storage"] == {
        "manifest": "ple-store.json",
        "cache_rows": 0,
    }
    index = json.loads((view / "model.safetensors.index.json").read_text())
    assert list(index["weight_map"]) == ["language_model.model.norm.weight"]
    manifest = json.loads((view / "ple-store.json").read_text())
    assert manifest["row_count"] == 8 and manifest["row_width"] == 160
    assert manifest["source_root"] == str(snapshot.resolve())
    assert (view / "model-00002-of-00002.safetensors").is_symlink()
    assert not (view / "model-00001-of-00002.safetensors").exists()
    assert (view / "tokenizer.json").resolve() == (
        snapshot / "tokenizer.json"
    ).resolve()


def test_reuses_current_view_and_rebuilds_for_new_snapshot(tmp_path: Path) -> None:
    first = _checkpoint(tmp_path / "first")
    view = prepare_external_ple_view(first, tmp_path / "view")
    stamp = (view / "config.json").stat().st_mtime_ns

    assert prepare_external_ple_view(first, view) == view
    assert (view / "config.json").stat().st_mtime_ns == stamp

    second = _checkpoint(tmp_path / "second")
    prepare_external_ple_view(second, view)
    marker = json.loads((view / "EXTERNAL_PLE.json").read_text())
    assert marker["source"] == str(second.resolve())
    assert not (tmp_path / "view.tmp").exists()
