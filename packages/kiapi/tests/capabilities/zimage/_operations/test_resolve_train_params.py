from kiapi.capabilities.zimage._operations.resolve_train_params import (
    resolve_train_params,
)
from kiapi.capabilities.zimage._settings import ZimageSettings
from kiapi.capabilities.zimage._views.train_request import TrainRequest


def test_resolve_train_params_applies_variant_defaults() -> None:
    settings = ZimageSettings(
        train_steps={"turbo": 9, "base": 20},
        train_timestep_low={"turbo": 4, "base": 0},
        train_quantize={"turbo": 8, "base": 8},
    )
    req = TrainRequest.model_validate(
        {"dataset": {"type": "file_id", "file_id": "file_dataset"}}
    )

    params = resolve_train_params(settings, req, variant="turbo")

    assert params.model == "turbo"
    assert params.steps == 9
    assert params.quantize == 8
    assert params.timestep_low == 4
    assert params.timestep_high == 9
    assert params.save_frequency == 10**9


def test_resolve_train_params_preserves_request_overrides() -> None:
    settings = ZimageSettings()
    req = TrainRequest.model_validate(
        {
            "dataset": {"type": "file_id", "file_id": "file_dataset"},
            "steps": 11,
            "quantize": 4,
            "timestep_low": 2,
            "timestep_high": 7,
            "save_frequency": 3,
        }
    )

    params = resolve_train_params(settings, req, variant="base")

    assert params.steps == 11
    assert params.quantize == 4
    assert params.timestep_low == 2
    assert params.timestep_high == 7
    assert params.save_frequency == 3
