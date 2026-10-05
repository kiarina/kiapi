"""Where kiapi keeps the mlx-serve release, its extracted binary, and the prompt guides."""

import hashlib
from pathlib import Path

from kiarina.utils.app import user_directory

from .._settings import H3Settings

PROMPT_GUIDES = ("base-en.txt", "ref-en.txt")


def mlx_serve_archive(settings: H3Settings) -> Path:
    return _base_dir(settings) / "mlx-serve-bin-macos-arm64.tar.gz"


def mlx_serve_binary(settings: H3Settings) -> Path:
    return _base_dir(settings) / "mlx-serve-macos-arm64" / "mlx-serve"


def prompt_guide(settings: H3Settings, name: str) -> Path:
    # Keyed by URL so a new pinned commit downloads fresh copies.
    key = hashlib.sha256(settings.prompt_guide_base_url.encode()).hexdigest()[:12]
    return user_directory.get_user_cache_dir() / "h3" / f"prompt-guides-{key}" / name


def _base_dir(settings: H3Settings) -> Path:
    return (
        user_directory.get_user_cache_dir()
        / "h3"
        / f"mlx-serve-{settings.mlx_serve_version}"
    )
