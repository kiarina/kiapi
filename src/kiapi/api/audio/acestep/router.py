"""Music API (acestep): ``POST /v1/audio/acestep/{generate,cover,repaint,extract}``.

Each endpoint is sync or async via ``mode``. generate validates the duration cap.
"""

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
from kiapi.capabilities.acestep import (
    CoverRequest,
    ExtractRequest,
    GenerateRequest,
    RepaintRequest,
    handle_cover,
    handle_extract,
    handle_generate,
    handle_repaint,
    settings_manager,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.extract_response import ExtractResponse
from ._views.track_response import TrackResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


def _validate_model(model: str) -> None:
    try:
        model_registry.resolve("acestep", model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904


@router.post(
    "/v1/audio/acestep/generate",
    responses=build_job_responses("audio/wav", result_model=TrackResponse),
)
async def generate_music(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate a brand-new song from a style prompt + lyrics (text2music).

    Takes no source track: `prompt` describes the SOUND, `lyrics` carries the
    section-tagged words (or `[Instrumental]`), and `duration`/`lang` shape the
    output. To restyle or edit an existing track use `/cover`, `/repaint`, or
    `/extract` instead. The same endpoint serves both `sync` and `async` via
    `mode`.

    Sync content negotiation: one WAV is produced, so unless the client asks for
    JSON the raw audio bytes are returned with `X-Kiapi-File-Id` / `X-Kiapi-Job-Id`
    headers — `curl -o out.wav` just works. With `Accept: application/json` (or
    async) the Job JSON is returned, whose `result` follows TrackResponse.

    Async returns 202 immediately; poll GET /v1/jobs/{job_id} and fetch the
    artifact via GET /v1/files/{file_id}.
    """
    _validate_model(req.model)
    cap = settings_manager.get_settings().max_duration
    if req.duration > cap:
        raise HTTPException(
            status_code=422, detail=f"duration {req.duration}s exceeds max {cap}s"
        )
    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="acestep.generate",
        params=req.gen_params() | {"model": req.model},
        thunk=lambda: handle_generate(ctx, req),
        mode=req.mode,
        accept=accept,
    )


@router.post(
    "/v1/audio/acestep/cover",
    responses=build_job_responses("audio/wav", result_model=TrackResponse),
)
async def cover_music(
    req: CoverRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Re-style an existing track while preserving its structure (cover).

    Requires a `source` track and a `prompt` describing the target style;
    `strength` (0..1) trades creative freedom against faithfulness to the source.
    To regenerate only a time range use `/repaint`; to make a song from scratch
    use `/generate`. The same endpoint serves both `sync` and `async` via `mode`.

    Sync content negotiation and the TrackResponse `result` shape match
    `/v1/audio/acestep/generate` (one WAV artifact; `result.src` references the
    source file_id).
    """
    _validate_model(req.model)
    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="acestep.cover",
        params=req.gen_params() | {"model": req.model},
        thunk=lambda: handle_cover(ctx, req),
        mode=req.mode,
        accept=accept,
    )


@router.post(
    "/v1/audio/acestep/repaint",
    responses=build_job_responses("audio/wav", result_model=TrackResponse),
)
async def repaint_music(
    req: RepaintRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Regenerate one time range of an existing track (repaint).

    Requires a `source` track, a `prompt` for the section's style, and a
    `start`/`end` window (`end=-1` runs to the end of the track); `strength`
    (0..1) controls how aggressively that window is regenerated while it blends
    into the rest. To restyle the whole track use `/cover`. The same endpoint
    serves both `sync` and `async` via `mode`.

    Sync content negotiation and the TrackResponse `result` shape match
    `/v1/audio/acestep/generate` (one WAV artifact; `result.src` references the
    source file_id).
    """
    _validate_model(req.model)
    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="acestep.repaint",
        params=req.gen_params() | {"model": req.model},
        thunk=lambda: handle_repaint(ctx, req),
        mode=req.mode,
        accept=accept,
    )


@router.post(
    "/v1/audio/acestep/extract",
    responses=build_job_responses("audio/wav", result_model=ExtractResponse),
)
async def extract_music(
    req: ExtractRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Separate a track into stems / source separation (extract).

    Requires a `source` track and a list of `targets` (e.g. vocals / drums / bass
    / other). One job produces one WAV stem per target, so `artifacts` holds a
    file_id per target. The same endpoint serves both `sync` and `async` via
    `mode`.

    Unlike the other operations this is a multi-artifact job, so sync always
    returns the Job JSON (no raw-bytes shortcut). The `result` follows
    ExtractResponse, whose `stems[]` carry one file_id each. Fetch each via
    GET /v1/files/{file_id}.
    """
    _validate_model(req.model)
    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="acestep.extract",
        params=req.gen_params() | {"model": req.model},
        thunk=lambda: handle_extract(ctx, req),
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="acestep", base_path="/v1/audio/acestep")
