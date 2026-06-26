import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.ltx2 import GenerateRequest, validate_generate


def test_validate_generate_accepts_default_request() -> None:
    req = GenerateRequest.model_validate({"prompt": "a calm ocean wave"})

    validate_generate(req, variant="distilled", has_audio=False)


def test_validate_generate_rejects_non_multiple_width() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "width": 300})

    with pytest.raises(ValidationError, match="positive multiple of 64"):
        validate_generate(req, variant="distilled", has_audio=False)


def test_validate_generate_rejects_frame_count_not_one_plus_eight_k() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "num_frames": 50})

    with pytest.raises(ValidationError, match=r"1 \+ 8\*k"):
        validate_generate(req, variant="distilled", has_audio=False)


def test_validate_generate_rejects_audio_file_with_generated_audio() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "generate_audio": True})

    with pytest.raises(ValidationError, match="cannot combine an audio file"):
        validate_generate(req, variant="distilled", has_audio=True)
