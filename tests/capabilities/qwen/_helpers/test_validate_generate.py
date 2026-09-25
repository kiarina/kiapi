import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.qwen import GenerateRequest, validate_generate


def test_validate_generate_accepts_image_21_default_request() -> None:
    req = GenerateRequest.model_validate({"prompt": "a small glass house"})

    validate_generate(req, variant="image-2.1")


def test_validate_generate_image_21_accepts_2k_multiple_of_32() -> None:
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "width": 2752, "height": 1536}
    )

    validate_generate(req, variant="image-2.1")


def test_validate_generate_image_21_rejects_multiple_of_16_only() -> None:
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "width": 1040, "height": 1024}
    )

    validate_generate(req, variant="image")
    with pytest.raises(ValidationError, match="multiples of 32"):
        validate_generate(req, variant="image-2.1")


def test_validate_generate_image_21_rejects_init_image() -> None:
    req = GenerateRequest.model_validate(
        {
            "prompt": "a small glass house",
            "init_image": {"type": "file_id", "file_id": "file_x"},
        }
    )

    with pytest.raises(ValidationError, match="init_image"):
        validate_generate(req, variant="image-2.1")


def test_validate_generate_image_21_rejects_loras() -> None:
    req = GenerateRequest.model_validate(
        {
            "prompt": "a small glass house",
            "loras": [{"file": {"type": "file_id", "file_id": "file_x"}}],
        }
    )

    with pytest.raises(ValidationError, match="loras"):
        validate_generate(req, variant="image-2.1")


def test_validate_generate_image_21_rejects_guidance_below_one() -> None:
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "guidance": 0.5}
    )

    with pytest.raises(ValidationError, match="guidance"):
        validate_generate(req, variant="image-2.1")


def test_validate_generate_image_21_rejects_single_step() -> None:
    req = GenerateRequest.model_validate({"prompt": "a small glass house", "steps": 1})

    validate_generate(req, variant="image")
    with pytest.raises(ValidationError, match="steps must be in 2"):
        validate_generate(req, variant="image-2.1")
