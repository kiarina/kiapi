from kiapi.capabilities.h3._operations.resolve_generate_params import (
    resolve_generate_params,
)
from kiapi.capabilities.h3._settings import H3Settings
from kiapi.capabilities.h3._views.generate_request import GenerateRequest


def test_resolve_generate_params_applies_turbo_defaults() -> None:
    req = GenerateRequest.model_validate({"prompt": "clouds drifting", "seed": 7})

    params = resolve_generate_params(H3Settings(), req, variant="ref2va-8bit")

    assert params.model == "ref2va-8bit"
    assert params.seed == 7
    assert (params.width, params.height, params.num_frames) == (960, 544, 124)
    assert params.turbo is True
    assert params.steps == 8
    assert params.fast is False


def test_resolve_generate_params_uses_base_steps_without_turbo() -> None:
    req = GenerateRequest.model_validate({"prompt": "x", "turbo": False})

    params = resolve_generate_params(H3Settings(), req, variant="ref2va-8bit")

    assert params.steps == 20


def test_resolve_generate_params_preserves_request_overrides() -> None:
    req = GenerateRequest.model_validate(
        {
            "prompt": "x",
            "width": 512,
            "height": 512,
            "num_frames": 56,
            "steps": 4,
            "fast": True,
            "use_video_audio": True,
        }
    )

    params = resolve_generate_params(H3Settings(), req, variant="ref2va-8bit")

    assert (params.width, params.height, params.num_frames) == (512, 512, 56)
    assert params.steps == 4
    assert params.fast is True
    assert params.use_video_audio is True
