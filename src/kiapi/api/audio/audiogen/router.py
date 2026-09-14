"""Sound-effect API: ``POST /v1/audio/audiogen/generate`` (sync or async via ``mode``)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from kiapi.api import (
    REQUIRE_AUTH,
    build_job_responses,
    get_accept,
    get_ctx,
    get_worker,
    register_capability_endpoints,
    submit_and_maybe_wait,
)
from kiapi.capabilities.audiogen import (
    GenerateRequest,
    ValidationError,
    handle_generate,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.audio_response import AudioResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/audio/audiogen/generate",
    responses=build_job_responses("audio/wav", result_model=AudioResponse),
)
async def generate_se(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate a short non-musical sound effect from a text prompt.

    Takes no source audio: `prompt` describes the sound event, environment, and
    texture, while `duration` and the sampling knobs shape the clip. AudioGen is
    for SFX/ambient audio such as rain, footsteps, impacts, machinery, or room
    tone; use `/v1/audio/acestep/generate` for music. The same endpoint serves
    both `sync` and `async` via `mode`.

    Sync content negotiation: one WAV is produced, so unless the client asks for
    JSON the raw audio bytes are returned with `X-Kiapi-File-Id` / `X-Kiapi-Job-Id`
    headers. With `Accept: application/json` (or async) the Job JSON is returned,
    whose `result` follows AudioResponse.

    Async returns 202 immediately; poll GET /v1/jobs/{job_id} and fetch the
    artifact via GET /v1/files/{file_id}.
    """
    # Validate up front so async callers also get immediate 400/422.
    try:
        spec = model_registry.resolve("audiogen", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_generate(req, variant=spec.name)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="audiogen",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=lambda: handle_generate(ctx, req),
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="audiogen", base_path="/v1/audio/audiogen")
