import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.zimage import GenerateRequest, validate_generate


def test_validate_generate_accepts_default_request() -> None:
    req = GenerateRequest.model_validate({"prompt": "a small glass house"})

    validate_generate(req, variant="turbo")


def test_validate_generate_rejects_non_multiple_size() -> None:
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "width": 1025, "height": 1024}
    )

    with pytest.raises(ValidationError, match="multiples of 16"):
        validate_generate(req, variant="turbo")


def test_validate_generate_rejects_invalid_quantize() -> None:
    req = GenerateRequest.model_validate(
        {"prompt": "a small glass house", "quantize": 7}
    )

    with pytest.raises(ValidationError, match="quantize must be one of"):
        validate_generate(req, variant="turbo")
