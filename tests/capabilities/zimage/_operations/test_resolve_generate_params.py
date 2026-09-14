from kiapi.capabilities.zimage._operations.resolve_generate_params import (
    resolve_generate_params,
)
from kiapi.capabilities.zimage._settings import ZimageSettings
from kiapi.capabilities.zimage._views.generate_request import GenerateRequest


def test_resolve_generate_params_applies_variant_defaults() -> None:
    settings = ZimageSettings(
        default_width=768,
        default_height=512,
        default_steps={"turbo": 9, "base": 28},
        default_guidance={"turbo": None, "base": 4.0},
        default_quantize={"turbo": None, "base": 8},
    )
    req = GenerateRequest.model_validate({"prompt": "a small glass house", "seed": 123})

    params = resolve_generate_params(settings, req, variant="base")

    assert params.model == "base"
    assert params.seed == 123
    assert params.width == 768
    assert params.height == 512
    assert params.steps == 28
    assert params.guidance == 4.0
    assert params.quantize == 8
    assert params.mode == "txt2img"


def test_resolve_generate_params_preserves_request_overrides() -> None:
    settings = ZimageSettings()
    req = GenerateRequest.model_validate(
        {
            "prompt": "a small glass house",
            "width": 1024,
            "height": 768,
            "steps": 12,
            "guidance": 1.5,
            "seed": 456,
            "quantize": 4,
            "format": "webp",
            "quality": 80,
        }
    )

    params = resolve_generate_params(settings, req, variant="turbo")

    assert params.width == 1024
    assert params.height == 768
    assert params.steps == 12
    assert params.guidance == 1.5
    assert params.seed == 456
    assert params.quantize == 4
    assert params.format == "webp"
    assert params.quality == 80
