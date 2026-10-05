"""Where kiapi keeps the mlx-serve release archive and its extracted binary."""

from pathlib import Path

from kiarina.utils.app import user_directory

from .._settings import H3Settings


def mlx_serve_archive(settings: H3Settings) -> Path:
    return _base_dir(settings) / "mlx-serve-bin-macos-arm64.tar.gz"


def mlx_serve_binary(settings: H3Settings) -> Path:
    return _base_dir(settings) / "mlx-serve-macos-arm64" / "mlx-serve"


def _base_dir(settings: H3Settings) -> Path:
    return (
        user_directory.get_user_cache_dir()
        / "h3"
        / f"mlx-serve-{settings.mlx_serve_version}"
    )
