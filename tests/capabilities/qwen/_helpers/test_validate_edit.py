import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.qwen import EditRequest, validate_edit


def _images(count: int) -> list[dict[str, str]]:
    return [{"type": "file_id", "file_id": f"file_{i}"} for i in range(count)]


def test_validate_edit_image_21_accepts_omitted_size() -> None:
    req = EditRequest.model_validate({"prompt": "make it blue", "images": _images(1)})

    validate_edit(req, variant="image-2.1")


def test_validate_edit_image_21_accepts_ten_images() -> None:
    req = EditRequest.model_validate({"prompt": "combine", "images": _images(10)})

    validate_edit(req, variant="image-2.1")


def test_validate_edit_image_21_rejects_eleven_images() -> None:
    req = EditRequest.model_validate({"prompt": "combine", "images": _images(11)})

    with pytest.raises(ValidationError, match="at most 10"):
        validate_edit(req, variant="image-2.1")


def test_validate_edit_image_21_rejects_non_multiple_of_32() -> None:
    req = EditRequest.model_validate(
        {"prompt": "make it blue", "images": _images(1), "width": 1040}
    )

    with pytest.raises(ValidationError, match="multiples of 32"):
        validate_edit(req, variant="image-2.1")
