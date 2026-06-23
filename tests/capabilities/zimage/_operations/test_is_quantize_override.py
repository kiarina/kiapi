from kiapi.capabilities.zimage._operations.is_quantize_override import (
    is_quantize_override,
)
from kiapi.capabilities.zimage._settings import ZimageSettings
from kiapi.capabilities.zimage._views.generate_request import GenerateRequest


def test_is_quantize_override_false_when_omitted() -> None:
    settings = ZimageSettings(default_quantize={"turbo": None, "base": 8})
    req = GenerateRequest.model_validate({"prompt": "a small glass house"})

    assert is_quantize_override(settings, req, variant="turbo") is False


def test_is_quantize_override_false_when_matches_default() -> None:
    settings = ZimageSettings(default_quantize={"turbo": None, "base": 8})
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "quantize": 8}
    )

    assert is_quantize_override(settings, req, variant="base") is False


def test_is_quantize_override_true_when_differs_from_default() -> None:
    settings = ZimageSettings(default_quantize={"turbo": None, "base": 8})
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "quantize": 4}
    )

    assert is_quantize_override(settings, req, variant="base") is True
