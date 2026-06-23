from kiapi.capabilities.audiogen._operations.resolve_generate_params import (
    resolve_generate_params,
)
from kiapi.capabilities.audiogen._settings import AudiogenSettings
from kiapi.capabilities.audiogen._views.generate_request import GenerateRequest


def test_resolve_generate_params_preserves_request_values() -> None:
    settings = AudiogenSettings()
    req = GenerateRequest.model_validate(
        {
            "prompt": "ocean waves crashing on rocks",
            "duration": 3.5,
            "seed": 42,
            "top_k": 100,
            "top_p": 0.5,
            "temperature": 0.8,
            "cfg_coef": 4.0,
        }
    )

    params = resolve_generate_params(settings, req, variant="medium")

    assert params.model == "medium"
    assert params.prompt == "ocean waves crashing on rocks"
    assert params.duration == 3.5
    assert params.seed == 42
    assert params.top_k == 100
    assert params.top_p == 0.5
    assert params.temperature == 0.8
    assert params.cfg_coef == 4.0


def test_resolve_generate_params_generates_seed_when_omitted() -> None:
    settings = AudiogenSettings()
    req = GenerateRequest.model_validate({"prompt": "keyboard typing"})

    params = resolve_generate_params(settings, req, variant="medium")

    assert params.model == "medium"
    assert 0 <= params.seed <= 2**31 - 1
