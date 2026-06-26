import os
from unittest.mock import patch

from kiapi.core.worker._settings import WorkerSettings


def test_worker_settings_defaults():  # type: ignore
    settings = WorkerSettings()
    assert settings.ttl_sweep_interval_s == 60.0
    assert settings.warmup_models == []


def test_worker_settings_with_warmup_models_json():  # type: ignore
    with patch.dict(
        os.environ, {"KIAPI_WARMUP_MODELS": '["modelA", "modelB"]'}, clear=True
    ):
        settings = WorkerSettings()
        assert settings.warmup_models == ["modelA", "modelB"]
