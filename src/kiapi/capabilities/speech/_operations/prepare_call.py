import hashlib
import io
from collections import OrderedDict
from typing import Any

from kiapi.core.app import AppContext
from kiapi.core.model import model_registry

from .._helpers.patch_mlx_audio import clear_pending_prime
from .._views.speech_request import SpeechRequest
from .handle_speech import resolve_speech_params


def prepare_call(
    ctx: AppContext, req: SpeechRequest, state: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    spec = model_registry.resolve("speech", req.model)
    params = resolve_speech_params(req, variant=spec.name, stream=True)
    if not params.reference_text:
        raise ValueError("Streaming clone requires a reference transcript")
    audio = params.reference_path.read_bytes()
    state.update(
        model=spec.name,
        voice=params.voice,
        language=params.lang_code,
        transcript=params.reference_text,
        audio=audio,
        seed=req.seed,
        digest=hashlib.sha256(audio).hexdigest(),
    )
    _, prepared = _acquire_prepared(ctx, state)
    return {
        "required_prefix_tokens": 1,
        "prepared_rows": prepared.prepared_rows,
        "prep_s": prepared.prep_s,
    }, []


def _acquire_prepared(ctx: AppContext, state: dict[str, Any]) -> tuple[Any, Any]:
    import mlx.core as mx
    import soundfile as sf  # type: ignore[import-untyped]

    from kiapi.capabilities.speech.live import prepare_clone, prepare_reference

    spec = model_registry.resolve("speech", state["model"])
    ctx.ensure_model_ready(spec)
    payload: Any = ctx.memory_manager.acquire(spec)
    cache = getattr(payload, "prepared_references", None)
    if cache is None:
        cache = payload.prepared_references = OrderedDict()
    key = (state["digest"], state["transcript"], state["language"])
    clear_pending_prime()
    if key not in cache:
        audio, rate = sf.read(io.BytesIO(state["audio"]), dtype="float32")
        if rate != 24000 or audio.ndim != 1:
            raise ValueError("Registered reference must be 24 kHz mono")
        prompt = prepare_clone(
            payload.model, mx.array(audio), state["transcript"], state["language"]
        )
        cache[key] = prepare_reference(payload.model, prompt)
        while len(cache) > 2:
            cache.popitem(last=False)
        payload.prepared_reference_bytes = sum(_state_bytes(p) for p in cache.values())
    cache.move_to_end(key)
    return payload, cache[key]


def _state_bytes(value: Any) -> int:
    if hasattr(value, "nbytes"):
        return int(value.nbytes)
    if isinstance(value, dict):
        return sum(_state_bytes(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return sum(_state_bytes(v) for v in value)
    if hasattr(value, "state"):
        return _state_bytes(value.state)
    if hasattr(value, "__dict__"):
        return _state_bytes(vars(value))
    return 0
