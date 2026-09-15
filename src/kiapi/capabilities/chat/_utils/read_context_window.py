"""Read a chat model's context window from its ``config.json``.

The value comes from the weights' own config rather than being hand-written, so
it follows the model. The config layout differs per model type, so each handler
module names the key path in ``CONTEXT_WINDOW_KEYS``. Returns None when the
config is not available locally (the model is not set up yet).
"""

import json
from pathlib import Path

from kiapi.core.model import ModelSpec


def read_context_window(spec: ModelSpec) -> int | None:
    path = _config_path(spec.repo)
    if path is None:
        return None
    value = json.loads(path.read_text())
    for key in spec.module.CONTEXT_WINDOW_KEYS:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, int) else None


def _config_path(repo: str) -> Path | None:
    local = Path(repo).expanduser() / "config.json"
    if local.is_file():
        return local

    from huggingface_hub import try_to_load_from_cache
    from huggingface_hub.errors import HFValidationError

    try:
        cached = try_to_load_from_cache(repo, "config.json")
    except HFValidationError:  # a local path that does not exist
        return None
    return Path(cached) if isinstance(cached, str) else None
