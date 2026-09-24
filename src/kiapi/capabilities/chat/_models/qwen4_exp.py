"""Handler for Qwen3.8-Flash-Next (``model_type: qwen4_exp``).

The chat template, Hermes/XML tool calls, thinking switch, and generate flow are
the same as Qwen3.8-27B, so generation is delegated to :mod:`qwen3_5`. Only
loading differs:

  - the checkpoint is loaded through an external-PLE view so the ~32 GB n-gram
    table is memory-mapped instead of resident (``prepare_external_ple_view``);
  - the open-file limit is raised, because the mapped PLE keeps 128 shards open.
"""

from pathlib import Path
from types import SimpleNamespace

from kiarina.utils.app import user_directory

from kiapi.core.model import ModelSpec

from .._operations.initialize_apc import initialize_apc
from .._operations.prepare_external_ple_view import prepare_external_ple_view
from .._utils.load_mlx_vlm import load_mlx_vlm
from .._utils.raise_open_file_limit import raise_open_file_limit
from .._utils.warmup_params import warmup_params
from . import qwen3_5

FEATURES = qwen3_5.FEATURES
CONTEXT_WINDOW_KEYS = ("text_config", "max_position_embeddings")

release = qwen3_5.release
resident_extra_bytes = qwen3_5.resident_extra_bytes
run = qwen3_5.run


def load(spec: ModelSpec) -> SimpleNamespace:
    from huggingface_hub import snapshot_download

    raise_open_file_limit()
    snapshot = Path(snapshot_download(spec.repo, local_files_only=True))
    view = prepare_external_ple_view(snapshot, _view_dir(spec.repo))
    payload = load_mlx_vlm(spec, view)
    initialize_apc(payload)
    return payload


def warmup(payload: SimpleNamespace) -> None:
    run(payload, warmup_params("qwen3.8-flash-next"))


def _view_dir(repo: str) -> Path:
    return (
        user_directory.get_user_cache_dir()
        / "chat"
        / "external-ple"
        / repo.replace("/", "--")
    )
