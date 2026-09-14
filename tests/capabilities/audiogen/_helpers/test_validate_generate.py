import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.audiogen import GenerateRequest, validate_generate


def test_validate_generate_accepts_default_request() -> None:
    req = GenerateRequest.model_validate({"prompt": "keyboard typing"})

    validate_generate(req, variant="medium")


def test_validate_generate_rejects_duration_over_cap() -> None:
    req = GenerateRequest.model_validate(
        {"prompt": "keyboard typing", "duration": 11.0}
    )

    with pytest.raises(ValidationError, match=r"duration 11\.0s exceeds max 10\.0s"):
        validate_generate(req, variant="medium")
