from pathlib import Path

from PIL import Image

from kiapi.capabilities.qwen._operations.resolve_edit_params import (
    resolve_edit_params,
)
from kiapi.capabilities.qwen._settings import QwenSettings
from kiapi.capabilities.qwen._views.edit_request import EditRequest


def _request(**kwargs: object) -> EditRequest:
    return EditRequest.model_validate(
        {
            "prompt": "make it blue",
            "images": [{"type": "file_id", "file_id": "file_x"}],
            **kwargs,
        }
    )


def _image(tmp_path: Path, size: tuple[int, int]) -> str:
    path = tmp_path / f"{size[0]}x{size[1]}.png"
    Image.new("RGB", size).save(path)
    return str(path)


def test_resolve_edit_params_image_21_defaults(tmp_path: Path) -> None:
    params = resolve_edit_params(
        QwenSettings(),
        _request(),
        variant="image-2.1",
        image_paths=[_image(tmp_path, (512, 512))],
    )

    assert (params.width, params.height) == (1024, 1024)
    assert (params.steps, params.guidance, params.quantize) == (40, 1.0, 8)
    assert params.reference_resolution == 1024


def test_resolve_edit_params_image_21_size_follows_last_reference(
    tmp_path: Path,
) -> None:
    params = resolve_edit_params(
        QwenSettings(),
        _request(),
        variant="image-2.1",
        image_paths=[_image(tmp_path, (512, 512)), _image(tmp_path, (1920, 1080))],
    )

    assert (params.width, params.height) == (1376, 768)


def test_resolve_edit_params_image_21_keeps_explicit_size(tmp_path: Path) -> None:
    params = resolve_edit_params(
        QwenSettings(),
        _request(width=2048, height=1024),
        variant="image-2.1",
        image_paths=[_image(tmp_path, (512, 512))],
    )

    assert (params.width, params.height) == (2048, 1024)


def test_resolve_edit_params_edit_2509_keeps_defaults(tmp_path: Path) -> None:
    params = resolve_edit_params(
        QwenSettings(),
        _request(),
        variant="edit-2509",
        image_paths=[_image(tmp_path, (1920, 1080))],
    )

    assert (params.width, params.height) == (1024, 1024)
    assert (params.steps, params.guidance) == (30, 2.5)
    assert params.reference_resolution is None
