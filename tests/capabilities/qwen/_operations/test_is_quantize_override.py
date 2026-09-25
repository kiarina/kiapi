from kiapi.capabilities.qwen._operations.is_quantize_override import (
    is_quantize_override,
)
from kiapi.capabilities.qwen._settings import QwenSettings
from kiapi.capabilities.qwen._views.generate_request import GenerateRequest


def test_is_quantize_override_uses_image_21_default() -> None:
    settings = QwenSettings(default_quantize=8, image_21_quantize=4)
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "quantize": 4}
    )

    assert is_quantize_override(settings, req, variant="image-2.1") is False
    assert is_quantize_override(settings, req, variant="image") is True


def test_is_quantize_override_false_when_omitted() -> None:
    settings = QwenSettings()
    req = GenerateRequest.model_validate({"prompt": "a small glass house"})

    assert is_quantize_override(settings, req, variant="image-2.1") is False
