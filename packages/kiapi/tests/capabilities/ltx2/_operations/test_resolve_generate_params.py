from kiapi.capabilities.ltx2._operations.resolve_generate_params import (
    resolve_generate_params,
)
from kiapi.capabilities.ltx2._settings import LTX2Settings
from kiapi.capabilities.ltx2._views.generate_request import GenerateRequest


def test_resolve_generate_params_applies_settings_defaults() -> None:
    settings = LTX2Settings(
        default_width=640,
        default_height=576,
        default_num_frames=49,
        default_fps=12,
    )
    req = GenerateRequest.model_validate({"prompt": "clouds drifting", "seed": 123})

    params = resolve_generate_params(settings, req, variant="distilled")

    assert params.model == "distilled"
    assert params.prompt == "clouds drifting"
    assert params.seed == 123
    assert params.width == 640
    assert params.height == 576
    assert params.num_frames == 49
    assert params.fps == 12


def test_resolve_generate_params_preserves_request_overrides() -> None:
    settings = LTX2Settings()
    req = GenerateRequest.model_validate(
        {
            "prompt": "a cat walking",
            "width": 256,
            "height": 320,
            "num_frames": 17,
            "fps": 8,
            "seed": 456,
            "image_strength": 0.7,
            "end_image_strength": 0.5,
            "generate_audio": True,
        }
    )

    params = resolve_generate_params(settings, req, variant="distilled")

    assert params.width == 256
    assert params.height == 320
    assert params.num_frames == 17
    assert params.fps == 8
    assert params.seed == 456
    assert params.image_strength == 0.7
    assert params.end_image_strength == 0.5
    assert params.generate_audio is True


def test_resolve_generate_params_generates_seed_when_omitted() -> None:
    settings = LTX2Settings()
    req = GenerateRequest.model_validate({"prompt": "keyboard typing"})

    params = resolve_generate_params(settings, req, variant="distilled")

    assert 0 <= params.seed <= 2**31 - 1
