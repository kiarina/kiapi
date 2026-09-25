import io
from pathlib import Path
from typing import Any

from PIL import Image

from kiapi.capabilities.qwen._operations import store_image as store_image_module
from kiapi.capabilities.qwen._operations.store_image import store_image


class _Record:
    file_id = "file_x"
    size = 1


class _Files:
    def __init__(self) -> None:
        self.content = b""

    def put_path(self, path: Path, **_: Any) -> _Record:
        self.content = path.read_bytes()
        return _Record()


def _rgba() -> Image.Image:
    image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    image.putpixel((0, 0), (255, 0, 0, 255))
    return image


def test_store_image_flattens_rgba_jpeg_onto_white(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(store_image_module, "create_work_dir", lambda _: tmp_path)
    files = _Files()

    store_image(_rgba(), fmt="jpeg", quality=100, files=files, meta={})  # type: ignore[arg-type]

    out = Image.open(io.BytesIO(files.content))
    assert out.mode == "RGB"
    pixel = out.getpixel((3, 3))
    assert isinstance(pixel, tuple)
    assert min(pixel) > 240


def test_store_image_keeps_png_alpha(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(store_image_module, "create_work_dir", lambda _: tmp_path)
    files = _Files()

    store_image(_rgba(), fmt="png", quality=90, files=files, meta={})  # type: ignore[arg-type]

    out = Image.open(io.BytesIO(files.content))
    assert out.mode == "RGBA"
    pixel = out.getpixel((3, 3))
    assert isinstance(pixel, tuple)
    assert pixel[3] == 0
