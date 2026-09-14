from kiapi.capabilities.acestep._operations.resolve_generate_params import (
    resolve_generate_params,
)
from kiapi.capabilities.acestep._views.generate_request import GenerateRequest


def test_resolve_generate_params_builds_model_contract() -> None:
    req = GenerateRequest(
        prompt="ambient piano",
        lyrics="[Instrumental]",
        duration=30,
        seed=123,
        inference_steps=8,
    )

    params = resolve_generate_params(req, variant="turbo")

    assert params.task == "text2music"
    assert params.model == "turbo"
    assert params.engine_params() == {
        "prompt": "ambient piano",
        "lyrics": "[Instrumental]",
        "duration": 30,
        "lang": "ja",
        "seed": 123,
        "inference_steps": 8,
        "guidance_scale": None,
        "shift": None,
    }
    assert params.meta_extra() == {"model": "turbo"}
