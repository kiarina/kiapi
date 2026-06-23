from kiapi.capabilities.acestep._operations.resolve_extract_params import (
    resolve_extract_params,
)
from kiapi.capabilities.acestep._views.extract_request import ExtractRequest
from kiapi.core.file import FileIDRef


def test_resolve_extract_params_builds_one_stem_contract() -> None:
    req = ExtractRequest(
        source=FileIDRef(file_id="file_audio"),
        targets=["vocals", "drums"],
        seed=9,
    )

    params = resolve_extract_params(
        req,
        variant="xl-base",
        source_file_id="file_audio",
        src_audio="/tmp/audio.wav",
        target="vocals",
    )

    assert params.task == "extract"
    assert params.model == "xl-base"
    assert params.engine_params() == {
        "src_audio": "/tmp/audio.wav",
        "target": "vocals",
        "seed": 9,
        "inference_steps": None,
        "guidance_scale": None,
        "shift": None,
    }
    assert params.meta_extra() == {
        "model": "xl-base",
        "src": "file_audio",
        "target": "vocals",
    }
