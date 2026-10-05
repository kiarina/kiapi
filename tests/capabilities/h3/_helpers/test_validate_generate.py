import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.h3 import GenerateRequest, validate_generate

IMAGE = {"type": "file_id", "file_id": "file_1"}


def test_validate_generate_accepts_default_request() -> None:
    validate_generate(GenerateRequest.model_validate({"prompt": "a calm ocean wave"}))


def test_validate_generate_rejects_non_multiple_of_32() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "width": 500})

    with pytest.raises(ValidationError, match="positive multiple of 32"):
        validate_generate(req)


def test_validate_generate_rejects_canvas_over_768p() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "width": 1344, "height": 800})

    with pytest.raises(ValidationError, match="exceeds max"):
        validate_generate(req)


@pytest.mark.parametrize("num_frames", [5, 50, 125])
def test_validate_generate_rejects_frames_off_the_ladder(num_frames: int) -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "num_frames": num_frames})

    with pytest.raises(ValidationError, match=r"5 \+ 17\*k"):
        validate_generate(req)


def test_validate_generate_rejects_frames_over_15_seconds() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "num_frames": 379})

    with pytest.raises(ValidationError, match="exceeds max 362"):
        validate_generate(req)


def test_validate_generate_rejects_more_than_12_references() -> None:
    req = GenerateRequest.model_validate(
        {
            "prompt": "x",
            "images": [IMAGE] * 9,
            "videos": [IMAGE] * 3,
            "audios": [IMAGE],
        }
    )

    with pytest.raises(ValidationError, match="at most 12 references"):
        validate_generate(req)


def test_validate_generate_rejects_audio_only_references() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "audios": [IMAGE]})

    with pytest.raises(ValidationError, match="need an image or video"):
        validate_generate(req)


def test_validate_generate_rejects_video_audio_without_videos() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "use_video_audio": True})

    with pytest.raises(ValidationError, match="at least one video"):
        validate_generate(req)


def test_request_rejects_more_than_nine_images() -> None:
    with pytest.raises(ValueError, match="at most 9"):
        GenerateRequest.model_validate({"prompt": "x", "images": [IMAGE] * 10})
